"""Quien abrio la historia de quien.

No habia ningun registro. En un consultorio con direccion, varios profesionales,
secretaria y coordinacion de area —todos con acceso a datos de pacientes— nadie
podia responder "¿quien miro esta historia?". Para datos de salud de terceros
(Ley 25.326) esa pregunta se contesta, y ademas es la primera que hace un
cliente cuando sospecha algo.

**Lo que se guarda y lo que no.** Quien, que y cuando. **Nunca el contenido**:
copiar aca lo que se leyo seria duplicar la historia clinica en una segunda
tabla, con las mismas obligaciones legales y menos cuidado encima.

**Append-only.** Este modulo no tiene funcion de borrar ni de actualizar, y no
es un olvido: un registro de accesos que el propio sistema puede reescribir no
prueba nada. Depurarlo, si algun dia hace falta, es una decision explicita y a
mano, como el borrado de un consultorio cancelado.

**Registrar nunca puede romper el pedido.** Si falla la escritura, el
profesional ve la historia igual. Un sistema clinico que deja de mostrar una
historia porque no pudo anotar la auditoria es peor que uno sin auditoria: en el
medio hay alguien esperando ser atendido.

⚠️ **No se registra lo que hace el paciente con lo suyo.** El portal es la
persona mirando sus propios estudios; anotarlo seria vigilarla, no auditar el
acceso de terceros a su historia — que es lo que la ley pide cuidar.
"""

from datetime import datetime

# A nivel de modulo y no dentro de cada funcion: los tests enganchan la base
# falsa al modulo (`make_db(monkeypatch, accesos)`), y un import local se queda
# con el real e intenta conectarse a MySQL de verdad. Ya paso con el freno de
# fuerza bruta: la suite entera se fue de 0,7 s a 120 s.
from app.database import db_cursor

# Las acciones que se anotan. Se enumeran para que la lista de una pantalla no
# dependa de que texto escribio cada quien: `ver` y `Ver` serian dos cosas.
VER_HISTORIA = "ver_historia"
VER_EVOLUCIONES = "ver_evoluciones"
EXPORTAR_HISTORIA = "exportar_historia"
EXPORTAR_EVOLUCION = "exportar_evolucion"
DESCARGAR_ADJUNTO = "descargar_adjunto"
ENVIAR_AL_PORTAL = "enviar_al_portal"

# Como se lee cada una. Vive aca y no en el `.vue` para que sumar una accion sea
# un solo lugar.
NOMBRES = {
    VER_HISTORIA: "Abrió la historia",
    VER_EVOLUCIONES: "Leyó las evoluciones",
    EXPORTAR_HISTORIA: "Descargó la historia en PDF",
    EXPORTAR_EVOLUCION: "Descargó una evolución en PDF",
    DESCARGAR_ADJUNTO: "Descargó un adjunto",
    ENVIAR_AL_PORTAL: "Le envió un documento al paciente",
}


def registrar(paciente_id, accion, detalle=None, usuario_id=None, ip=None):
    """Anota un acceso. No propaga errores.

    `usuario_id` e `ip` se toman del pedido en curso si no se pasan, para que
    quien llama no tenga que acordarse. Fuera de un request hay que pasarlos.
    """
    try:
        paciente_id = int(paciente_id)
    except (TypeError, ValueError):
        return

    if usuario_id is None or ip is None:
        try:
            from flask import request
            from flask_login import current_user

            if usuario_id is None:
                usuario_id = getattr(current_user, "id", None)
                # Un paciente del portal no es un usuario del consultorio: su id
                # apunta a otra base y guardarlo aca senalaria a la persona
                # equivocada. Mejor NULL, que se lee como "no fue el personal".
                if getattr(current_user, "es_paciente", False):
                    usuario_id = None
            if ip is None:
                ip = request.remote_addr
        except Exception:
            pass

    try:
        with db_cursor(commit=True) as (_conn, cur):
            cur.execute(
                """
                INSERT INTO accesos_historia
                    (usuario_id, paciente_id, accion, detalle, ip, creado_en)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    usuario_id,
                    paciente_id,
                    str(accion)[:30],
                    (str(detalle)[:255] if detalle else None),
                    (str(ip)[:60] if ip else None),
                    datetime.now(),
                ),
            )
    except Exception:
        # Ver arriba: el profesional ve la historia igual.
        return


def de_paciente(paciente_id, limite=200):
    """Quien accedio a la historia de este paciente, lo mas reciente primero.

    El limite es alto pero existe: una historia muy consultada podria devolver
    miles de filas a una pantalla que muestra las ultimas.
    """
    with db_cursor() as (_conn, cur):
        cur.execute(
            """
            SELECT a.id, a.accion, a.detalle, a.ip, a.creado_en,
                   a.usuario_id,
                   TRIM(CONCAT(COALESCE(u.nombre, ''), ' ', COALESCE(u.apellido, ''))) AS usuario,
                   u.rol
            FROM accesos_historia a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.paciente_id = %s
            ORDER BY a.creado_en DESC, a.id DESC
            LIMIT %s
            """,
            (int(paciente_id), int(limite)),
        )
        return [_serializar(f) for f in cur.fetchall()]


def de_usuario(usuario_id, limite=200):
    """A que historias accedio una persona. Es la otra mitad de la pregunta.

    Sirve para lo que realmente se investiga: no "quien vio esta historia" sino
    "que estuvo mirando esta persona".
    """
    with db_cursor() as (_conn, cur):
        cur.execute(
            """
            SELECT a.id, a.accion, a.detalle, a.ip, a.creado_en,
                   a.usuario_id, a.paciente_id,
                   TRIM(CONCAT(COALESCE(p.apellido, ''), ' ', COALESCE(p.nombre, ''))) AS paciente,
                   p.nro_hc
            FROM accesos_historia a
            LEFT JOIN pacientes p ON p.id = a.paciente_id
            WHERE a.usuario_id = %s
            ORDER BY a.creado_en DESC, a.id DESC
            LIMIT %s
            """,
            (int(usuario_id), int(limite)),
        )
        return [_serializar(f) for f in cur.fetchall()]


def _serializar(fila):
    from app.utils.fechas import a_iso_arg

    salida = {
        "id": fila["id"],
        "accion": fila["accion"],
        # El texto legible sale del servidor: sumar una accion es un solo lugar.
        "accion_nombre": NOMBRES.get(fila["accion"], fila["accion"]),
        "detalle": fila.get("detalle"),
        "ip": fila.get("ip"),
        # a_iso_arg() y no el datetime crudo: jsonify serializa los DATETIME
        # etiquetados como GMT aunque esten en hora argentina, y quien los lea
        # como UTC los corre tres horas. Ya paso tres veces en este proyecto.
        "cuando": a_iso_arg(fila["creado_en"]),
        "usuario_id": fila.get("usuario_id"),
    }
    if "usuario" in fila:
        # Sin usuario_id la fila es de alguien que ya no esta o de un acceso sin
        # sesion del personal. Se dice, en vez de mostrar un renglon en blanco.
        salida["usuario"] = (fila.get("usuario") or "").strip() or "—"
        salida["rol"] = fila.get("rol")
    if "paciente" in fila:
        salida["paciente"] = (fila.get("paciente") or "").strip() or "—"
        salida["paciente_id"] = fila.get("paciente_id")
        salida["nro_hc"] = fila.get("nro_hc")
    return salida
