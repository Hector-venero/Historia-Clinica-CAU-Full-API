"""Reserva de turnos desde el portal del paciente.

Es **el unico lugar donde el portal escribe en la base de un consultorio**, y por
eso esta todo junto y acotado en vez de repartido por las rutas.

El problema, dicho con precision: el paciente vive en el plano del portal, pero
su turno tiene que existir en `hc_<slug>` y apuntar a un `pacientes.id` de esa
misma base. Reservar es, inevitablemente, una escritura que cruza planos.

La solucion no es reimplementar la logica de agenda contra otra conexion, sino
**cambiar de contexto**: se pone el consultorio destino en `flask.g` y se llaman
las mismas funciones que usa el personal desde su pantalla. `get_connection()` ya
resuelve la base por ahi, asi que `medico_disponible()`, `_alinear_turno_individual()`
y `proximos_slots_libres()` funcionan sin tocarlas.

Que el calculo de horarios sea literalmente el mismo para los dos canales no es
una comodidad: dos implementaciones divergirian y terminarian ofreciendo
horarios distintos para la misma agenda.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta

import mysql.connector
from flask import g

from app import plataforma, portal

# Con cuanta anticipacion se puede reservar. Sin un limite, alguien puede pedir
# turno para dentro de tres anios y ocupar un horario que el profesional todavia
# no sabe si va a trabajar.
DIAS_MAXIMOS_ANTICIPACION = 60

# Cuanto antes del turno se corta la reserva online. Un turno para dentro de diez
# minutos no le da tiempo al consultorio a verlo.
HORAS_MINIMAS_ANTICIPACION = 2

# Hasta cuando se puede cancelar online.
#
# Pasado ese punto se pide llamar al consultorio, y no es burocracia: una
# cancelacion de ultimo momento que entra al sistema y nadie mira es peor que un
# llamado, porque el consultorio sigue esperando al paciente igual.
HORAS_MINIMAS_CANCELACION = 4


class ErrorReserva(Exception):
    """Algo que el paciente puede corregir. El mensaje se le muestra tal cual."""


@contextmanager
def como_consultorio(cliente):
    """Ejecuta el bloque como si el pedido perteneciera a ese consultorio.

    Es lo que permite reutilizar toda la logica de agenda existente: esas
    funciones piden la conexion a `database.get_connection()`, que resuelve el
    consultorio de `flask.g`.

    Restaura el valor anterior pase lo que pase. Sin el finally, una excepcion
    dejaria el resto del pedido apuntando a la base de otro consultorio, que es
    exactamente el tipo de fuga que toda esta arquitectura evita.
    """
    anterior = getattr(g, "cliente", None)
    g.cliente = cliente
    try:
        yield cliente
    finally:
        g.cliente = anterior


# ------------------------------------------------------------- directorio


def buscar_profesionales(texto=None, especialidad=None, limite=40):
    """Profesionales que aceptan turnos online.

    Lee la proyeccion del plano de control y no las bases de los consultorios:
    recorrerlas serian N consultas por busqueda, en la consulta mas usada del
    sitio publico y hecha por alguien sin sesion.
    """
    condiciones = []
    parametros = []

    if texto:
        condiciones.append(
            "(nombre LIKE %s OR apellido LIKE %s OR especialidad LIKE %s "
            "OR consultorio_nombre LIKE %s)"
        )
        patron = f"%{texto.strip()}%"
        parametros.extend([patron] * 4)

    if especialidad:
        condiciones.append("especialidad = %s")
        parametros.append(especialidad.strip())

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    with plataforma.cursor_plataforma() as (_conn, cur):
        cur.execute(
            f"""
            SELECT cliente_id, usuario_id, nombre, apellido, especialidad,
                   presentacion, lugar_nombre, lugar_direccion,
                   consultorio_slug, consultorio_nombre, duracion_turno
            FROM profesionales_publicos
            {where}
            ORDER BY apellido, nombre
            LIMIT %s
            """,
            (*parametros, int(limite)),
        )
        return cur.fetchall()


def especialidades_disponibles():
    """Para poblar el filtro del buscador, sin inventar una lista fija."""
    with plataforma.cursor_plataforma() as (_conn, cur):
        cur.execute(
            "SELECT especialidad, COUNT(*) AS n FROM profesionales_publicos "
            "WHERE especialidad IS NOT NULL AND especialidad <> '' "
            "GROUP BY especialidad ORDER BY especialidad"
        )
        return cur.fetchall()


def profesional_publico(cliente_id, usuario_id):
    with plataforma.cursor_plataforma() as (_conn, cur):
        cur.execute(
            "SELECT * FROM profesionales_publicos "
            "WHERE cliente_id = %s AND usuario_id = %s",
            (cliente_id, usuario_id),
        )
        return cur.fetchone()


def sincronizar_directorio(cliente):
    """Vuelca al directorio los profesionales del consultorio con agenda publica.

    Se llama cuando alguien guarda su perfil publico. Es un reemplazo completo
    para ese consultorio y no un UPDATE fila por fila: asi apagar la agenda
    publica de alguien lo saca del directorio, que con un UPDATE quedaria
    figurando para siempre.
    """
    from app.database import db_cursor

    with como_consultorio(cliente):
        with db_cursor() as (_conn, cur):
            cur.execute(
                """
                SELECT id, nombre, apellido, especialidad, presentacion_publica,
                       matricula_numero, lugar_atencion_nombre,
                       lugar_atencion_direccion, duracion_turno
                FROM usuarios
                WHERE activo = 1 AND agenda_publica = 1
                  AND rol IN ('profesional', 'director')
                """
            )
            profesionales = cur.fetchall()

    with plataforma.cursor_plataforma(commit=True) as (_conn, cur):
        cur.execute(
            "DELETE FROM profesionales_publicos WHERE cliente_id = %s", (cliente.id,)
        )
        for p in profesionales:
            cur.execute(
                """
                INSERT INTO profesionales_publicos
                    (cliente_id, usuario_id, nombre, apellido, especialidad,
                     presentacion, matricula, lugar_nombre, lugar_direccion,
                     consultorio_slug, consultorio_nombre, duracion_turno)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    cliente.id, p["id"], p["nombre"], p.get("apellido"),
                    p.get("especialidad"), p.get("presentacion_publica"),
                    p.get("matricula_numero"), p.get("lugar_atencion_nombre"),
                    p.get("lugar_atencion_direccion"), cliente.slug, cliente.nombre,
                    int(p.get("duracion_turno") or 20),
                ),
            )

    return len(profesionales)


# --------------------------------------------------------------- horarios


def horarios_libres(cliente_id, usuario_id, fecha, cantidad=20):
    """Horarios disponibles de un profesional para un dia.

    Se calcula con `proximos_slots_libres()`, la misma funcion que usa el
    sistema del consultorio: si fueran dos implementaciones distintas, el portal
    y la pantalla del profesional ofrecerian horarios distintos para la misma
    agenda.
    """
    ficha = profesional_publico(cliente_id, usuario_id)
    if ficha is None:
        # Mismo mensaje que si no existiera: un profesional que no publico su
        # agenda no tiene por que ser descubrible probando ids.
        raise ErrorReserva("El profesional no acepta turnos online.")

    cliente = plataforma.buscar_por_slug(ficha["consultorio_slug"])
    if cliente is None or not cliente.activo:
        raise ErrorReserva("El consultorio no esta disponible en este momento.")

    try:
        dia = datetime.strptime(fecha, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise ErrorReserva("Fecha invalida.")

    ahora = datetime.now()
    minimo = ahora + timedelta(hours=HORAS_MINIMAS_ANTICIPACION)
    maximo = ahora + timedelta(days=DIAS_MAXIMOS_ANTICIPACION)

    if dia.date() > maximo.date():
        raise ErrorReserva(
            f"Solo se puede reservar hasta {DIAS_MAXIMOS_ANTICIPACION} dias antes."
        )

    # Se arranca desde la apertura del dia, salvo que sea hoy: ahi desde el
    # minimo de anticipacion, para no ofrecer un horario que ya paso.
    desde = dia
    if dia.date() == ahora.date():
        desde = max(dia, minimo)
    elif dia.date() < ahora.date():
        return []

    from app.routes.turnos_routes import proximos_slots_libres

    with como_consultorio(cliente):
        slots = proximos_slots_libres(usuario_id, desde, cantidad=cantidad)

    # proximos_slots_libres busca hacia adelante y puede saltar al dia siguiente
    # si el que se pidio esta lleno. Aca interesa solo el dia consultado.
    del_dia = [s for s in slots if s.startswith(fecha)]
    return del_dia


# ---------------------------------------------------------------- reserva


def reservar(paciente, cliente_id, usuario_id, fecha_inicio, motivo=None):
    """Crea el turno en la base del consultorio y lo anota en el portal.

    Los cuatro pasos, en orden y con su razon:

      1. Resolver el consultorio destino y su conexion.
      2. Buscar o crear la fila de `pacientes` de ESA base. El paciente existe en
         el portal, pero `turnos.paciente_id` apunta a la tabla local: si nunca
         se atendio ahi, hay que crearlo.
      3. Crear el turno, con la misma logica de alineacion y disponibilidad que
         usa el personal.
      4. Dejar el registro en el plano del portal para que el paciente lo vea.
    """
    ficha = profesional_publico(cliente_id, usuario_id)
    if ficha is None:
        raise ErrorReserva("El profesional no acepta turnos online.")

    cliente = plataforma.buscar_por_slug(ficha["consultorio_slug"])
    if cliente is None or not cliente.activo:
        raise ErrorReserva("El consultorio no esta disponible en este momento.")

    from app.database import db_cursor
    from app.routes.turnos_routes import _alinear_turno_individual, medico_disponible

    with como_consultorio(cliente):
        inicio, fin, _ajuste, error = _alinear_turno_individual(usuario_id, fecha_inicio)
        if error:
            raise ErrorReserva(error)

        ahora = datetime.now()
        if inicio < ahora + timedelta(hours=HORAS_MINIMAS_ANTICIPACION):
            raise ErrorReserva(
                f"Hay que reservar con al menos {HORAS_MINIMAS_ANTICIPACION} horas "
                "de anticipacion."
            )
        if inicio > ahora + timedelta(days=DIAS_MAXIMOS_ANTICIPACION):
            raise ErrorReserva(
                f"Solo se puede reservar hasta {DIAS_MAXIMOS_ANTICIPACION} dias antes."
            )

        # medico_disponible() recibe las fechas como texto: es la firma con la
        # que la llama el resto del sistema, y _alinear_turno_individual()
        # devuelve datetime. Convertir aca y no cambiarle la firma evita tocar
        # las llamadas existentes, que funcionan.
        if not medico_disponible(usuario_id, inicio.isoformat(), fin.isoformat()):
            raise ErrorReserva("Ese horario ya no esta disponible.")

        with db_cursor() as (conn, cur):
            paciente_local_id = _buscar_o_crear_paciente(cur, conn, paciente)

            try:
                cur.execute(
                    """
                    INSERT INTO turnos
                        (paciente_id, usuario_id, fecha_inicio, fecha_fin, motivo,
                         observaciones)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        paciente_local_id, usuario_id, inicio, fin,
                        (motivo or "Turno solicitado online").strip()[:255],
                        "Reservado por el paciente desde el portal",
                    ),
                )
                conn.commit()
                turno_id = cur.lastrowid
            except mysql.connector.IntegrityError:
                # La restriccion UNIQUE (usuario_id, fecha_inicio) de la base.
                #
                # medico_disponible() ya lo comprobo, pero entre esa consulta y
                # este INSERT hay una ventana: con reserva online dos pacientes
                # pueden confirmar el mismo horario a la vez y pasar los dos la
                # comprobacion. Este es el caso que la aplicacion no puede ver y
                # la base si.
                conn.rollback()
                raise ErrorReserva(
                    "Alguien acaba de tomar ese horario. Elegi otro, por favor."
                )

    _registrar_en_portal(paciente, ficha, inicio, turno_id)
    _anotar_turno_del_paciente(
        paciente, ficha, cliente_id, usuario_id, turno_id, inicio, motivo
    )

    return {
        "turno_id": turno_id,
        "fecha_inicio": inicio.isoformat(sep=" "),
        "fecha_fin": fin.isoformat(sep=" "),
        "profesional": f"{ficha['nombre']} {ficha.get('apellido') or ''}".strip(),
        "consultorio": ficha["consultorio_nombre"],
        "lugar": ficha.get("lugar_direccion"),
    }


def _anotar_turno_del_paciente(paciente, ficha, cliente_id, usuario_id,
                               turno_id, inicio, motivo):
    """Deja el puntero al turno para que el paciente pueda verlo y cancelarlo.

    Es un puntero, no la verdad: el turno vive en la base del consultorio. Se
    guarda igual el detalle para poder mostrar la lista sin ir a buscarlo.
    """
    with portal.cursor_portal(commit=True) as (_conn, cur):
        cur.execute(
            """
            INSERT INTO turnos_reservados
                (tipo_documento, numero_documento, cliente_id, consultorio_slug,
                 consultorio_nombre, turno_id, usuario_id, profesional_nombre,
                 lugar, motivo, fecha_inicio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                paciente.tipo_documento, paciente.numero_documento, cliente_id,
                ficha["consultorio_slug"], ficha["consultorio_nombre"], turno_id,
                usuario_id,
                f"{ficha['nombre']} {ficha.get('apellido') or ''}".strip(),
                ficha.get("lugar_direccion"), (motivo or "").strip()[:255] or None,
                inicio,
            ),
        )


def mis_turnos(paciente, incluir_pasados=False):
    """Los turnos del paciente, verificados contra cada consultorio.

    No se confia en la copia del portal: el consultorio es quien manda, y si
    cancelo o reprogramo el turno desde su sistema, la copia quedo vieja. Se
    verifica con **una consulta por consultorio** con el que el paciente tenga
    turnos, que en la practica es uno o dos.
    """
    condicion = "" if incluir_pasados else "AND (fecha_inicio >= NOW() OR estado = 'cancelado')"

    with portal.cursor_portal() as (_conn, cur):
        cur.execute(
            f"""
            SELECT * FROM turnos_reservados
            WHERE tipo_documento = %s AND numero_documento = %s {condicion}
            ORDER BY fecha_inicio DESC
            """,
            (paciente.tipo_documento, paciente.numero_documento),
        )
        filas = cur.fetchall()

    # Se agrupan por consultorio para no abrir una conexion por turno.
    por_consultorio = {}
    for fila in filas:
        if fila["estado"] == "reservado":
            por_consultorio.setdefault(fila["consultorio_slug"], []).append(fila["turno_id"])

    # Ademas de saber si el turno sigue vivo, se trae la modalidad: un turno
    # puede haber pasado a videoconsulta despues de reservado, y el enlace tiene
    # que llegarle al paciente sin reenviarle nada. La copia del portal no lo
    # sabe; el consultorio si.
    vigentes = {}
    for slug, ids in por_consultorio.items():
        cliente = plataforma.buscar_por_slug(slug)
        if cliente is None:
            # El consultorio se dio de baja: sus turnos ya no existen, pero el
            # paciente tiene que seguir viendo que los tuvo.
            continue
        try:
            from app.database import db_cursor

            with como_consultorio(cliente):
                with db_cursor() as (_conn, cur):
                    marcas = ", ".join(["%s"] * len(ids))
                    cur.execute(
                        f"SELECT id, modalidad, enlace_video FROM turnos WHERE id IN ({marcas})",
                        tuple(ids),
                    )
                    vigentes.update(((slug, f["id"]), f) for f in cur.fetchall())
        except Exception:
            # Un consultorio caido no puede dejar al paciente sin ver su lista.
            # Se asume vigente: es lo que dice la copia. Sin modalidad, porque
            # eso solo lo sabe el consultorio y no se inventa.
            vigentes.update(((slug, i), None) for i in ids)

    resultado = []
    for fila in filas:
        clave = (fila["consultorio_slug"], fila["turno_id"])
        if fila["estado"] == "reservado" and clave not in vigentes:
            # Lo cancelo el consultorio desde su sistema.
            fila["estado"] = "cancelado"
            fila["cancelado_por"] = "consultorio"

        actual = vigentes.get(clave) or {}
        fila["modalidad"] = actual.get("modalidad") or "presencial"
        fila["enlace_video"] = actual.get("enlace_video")
        fila["puede_cancelar"] = _puede_cancelarse(fila)
        resultado.append(fila)

    return resultado


def _puede_cancelarse(fila):
    if fila["estado"] != "reservado":
        return False
    inicio = fila["fecha_inicio"]
    if not isinstance(inicio, datetime):
        return False
    return inicio > datetime.now() + timedelta(hours=HORAS_MINIMAS_CANCELACION)


def cancelar(paciente, reserva_id):
    """Cancela un turno reservado desde el portal.

    Borra el turno en la base del consultorio —que es como se cancela ahi, no hay
    columna de estado— y marca la copia del portal. El horario queda libre para
    otro paciente en el acto, que es justamente el sentido de que pueda
    cancelarse.
    """
    with portal.cursor_portal() as (_conn, cur):
        # El dueño va en el WHERE, no en una comprobacion posterior: asi no hay
        # forma de escribirla al reves y dejar que alguien cancele el turno de otro.
        cur.execute(
            "SELECT * FROM turnos_reservados "
            "WHERE id = %s AND tipo_documento = %s AND numero_documento = %s",
            (reserva_id, paciente.tipo_documento, paciente.numero_documento),
        )
        fila = cur.fetchone()

    if fila is None:
        raise ErrorReserva("No encontramos ese turno.")

    if fila["estado"] != "reservado":
        raise ErrorReserva("Ese turno ya estaba cancelado.")

    if not _puede_cancelarse(fila):
        raise ErrorReserva(
            f"Para cancelar con menos de {HORAS_MINIMAS_CANCELACION} horas de "
            "anticipacion, llama al consultorio."
        )

    cliente = plataforma.buscar_por_slug(fila["consultorio_slug"])
    if cliente is None:
        raise ErrorReserva("El consultorio ya no esta disponible.")

    from app.database import db_cursor

    with como_consultorio(cliente):
        with db_cursor(dictionary=False) as (conn, cur):
            cur.execute("DELETE FROM turnos WHERE id = %s", (fila["turno_id"],))
            conn.commit()

    with portal.cursor_portal(commit=True) as (_conn, cur):
        cur.execute(
            "UPDATE turnos_reservados SET estado = 'cancelado', "
            "cancelado_en = NOW(), cancelado_por = 'paciente' WHERE id = %s",
            (reserva_id,),
        )

    return fila


def _buscar_o_crear_paciente(cur, conn, paciente):
    """La fila de `pacientes` del consultorio que corresponde a esta persona.

    Se busca por documento, que es la misma llave con la que el portal identifica
    a alguien. Si el paciente nunca se atendio ahi, se crea con lo minimo: el
    resto de la ficha la completa el consultorio cuando lo atienda.
    """
    cur.execute(
        "SELECT id FROM pacientes WHERE dni = %s", (paciente.numero_documento,)
    )
    fila = cur.fetchone()
    if fila:
        return fila["id"]

    # nro_hc es UNIQUE y obligatorio. Se deriva del documento para no chocar con
    # la numeracion que lleve el consultorio.
    nro_hc = f"P-{paciente.numero_documento}"[:20]

    cur.execute(
        """
        INSERT INTO pacientes (nro_hc, dni, nombre, apellido, email, telefono)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            nro_hc, paciente.numero_documento,
            (paciente.nombre or "").upper(), (paciente.apellido or "").upper(),
            paciente.email, paciente.telefono,
        ),
    )
    conn.commit()
    return cur.lastrowid


def _registrar_en_portal(paciente, ficha, inicio, turno_id):
    """Anota el turno en el buzon del paciente.

    Se guarda como un documento de tipo `indicacion` y no en una tabla propia:
    para el paciente es una cosa mas que le llego de un consultorio, y asi
    aparece en la misma lista, ordenada por fecha, sin una pantalla aparte.
    """
    cuando = inicio.strftime("%d/%m/%Y a las %H:%M")
    profesional = f"{ficha['nombre']} {ficha.get('apellido') or ''}".strip()

    detalle = f"Turno confirmado para el {cuando}."
    if ficha.get("lugar_direccion"):
        detalle += f" En {ficha['lugar_direccion']}."

    portal.guardar_documento(
        tipo_documento=paciente.tipo_documento,
        numero_documento=paciente.numero_documento,
        consultorio_slug=ficha["consultorio_slug"],
        consultorio_nombre=ficha["consultorio_nombre"],
        profesional_nombre=profesional,
        tipo="indicacion",
        titulo=f"Turno con {profesional} — {cuando}",
        descripcion=detalle,
    )
