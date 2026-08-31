"""Agenda publica: que un profesional se ofrezca para turnos online.

Es la pieza que le faltaba al directorio. Hasta ahora `agenda_publica` solo se
podia encender con SQL a mano, asi que en la practica nadie podia publicarse y el
buscador de pacientes quedaba vacio.

**Viene apagada.** Publicar la agenda de alguien sin que lo pida seria repartir su
tiempo: un desconocido podria ocuparle un horario sin hablar antes. Encenderla es
una decision de cada profesional, no del consultorio ni de la plataforma.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import marca
from app.database import db_cursor
from app.tenancy import cliente_actual
from app.utils.permisos import requiere_rol

bp_agenda_publica = Blueprint("agenda_publica", __name__)

# Solo quien atiende pacientes. Un administrativo no tiene agenda propia que
# publicar.
ROLES_CON_AGENDA = ("profesional", "director")

# Lo que el directorio necesita para que la ficha sirva de algo. Sin esto el
# paciente ve un nombre suelto y no sabe ni de que atiende ni donde.
CAMPOS_REQUERIDOS = {
    # `apellido` es el que marca que alguien completo quien es la persona.
    #
    # El alta crea el usuario admin con el **nombre del consultorio**, porque es
    # lo unico que se le pide a quien se registra. Si se publica asi, el paciente
    # ve "Consultorio Dr. Lopez" donde tendria que ver a su profesional, y abajo
    # el nombre del consultorio otra vez.
    #
    # Se exige aca y no en el alta a proposito: este es el momento exacto en que
    # ese dato pasa a estar a la vista de desconocidos. Pedirlo al registrarse
    # seria un campo obligatorio mas en el formulario donde se pierde gente.
    "apellido": "tu apellido",
    "especialidad": "la especialidad",
    "lugar_atencion_direccion": "la direccion donde atendes",
}


def _estado_actual():
    with db_cursor() as (_conn, cur):
        cur.execute(
            """
            SELECT agenda_publica, presentacion_publica, especialidad, apellido,
                   duracion_turno, lugar_atencion_nombre, lugar_atencion_direccion
            FROM usuarios WHERE id = %s
            """,
            (current_user.id,),
        )
        return cur.fetchone()


def _faltantes(fila):
    """Que datos impiden publicarse. Se informan todos juntos y no de a uno:
    guardar cuatro veces para que cada vez falte otra cosa es exasperante."""
    return [
        etiqueta
        for campo, etiqueta in CAMPOS_REQUERIDOS.items()
        if not (fila.get(campo) or "").strip()
    ]


@bp_agenda_publica.route("/api/agenda-publica", methods=["GET"])
@login_required
@requiere_rol(*ROLES_CON_AGENDA)
def obtener():
    """Como esta configurada la agenda publica de quien pregunta."""
    fila = _estado_actual()
    if fila is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify({
        "activa": bool(fila.get("agenda_publica")),
        "presentacion": fila.get("presentacion_publica") or "",
        "especialidad": fila.get("especialidad") or "",
        "duracion_turno": fila.get("duracion_turno") or 20,
        "lugar_nombre": fila.get("lugar_atencion_nombre") or "",
        "lugar_direccion": fila.get("lugar_atencion_direccion") or "",
        "faltantes": _faltantes(fila),
        # Como lo va a ver un paciente en el buscador. Que el profesional lo lea
        # antes de publicarse evita la sorpresa de aparecer distinto de como
        # esperaba.
        "vista_previa": {
            "nombre": f"{current_user.nombre} {getattr(current_user, 'apellido', '') or ''}".strip(),
            "consultorio": marca.nombre_corto(),
        },
    })


@bp_agenda_publica.route("/api/agenda-publica", methods=["POST"])
@login_required
@requiere_rol(*ROLES_CON_AGENDA)
def guardar():
    """Enciende o apaga la agenda publica y actualiza el directorio."""
    datos = request.get_json(silent=True) or {}
    activar = bool(datos.get("activa"))
    presentacion = (datos.get("presentacion") or "").strip()[:300] or None

    if activar:
        # Se comprueba contra lo que va a quedar guardado, no contra lo que hay:
        # si el profesional completa la direccion en el mismo formulario, no
        # tiene por que guardar dos veces.
        fila = dict(_estado_actual() or {})
        for campo in CAMPOS_REQUERIDOS:
            if datos.get(campo) is not None:
                fila[campo] = datos.get(campo)

        faltan = _faltantes(fila)
        if faltan:
            return jsonify({
                "error": "Antes de publicarte falta " + " y ".join(faltan) + ".",
                "faltantes": faltan,
            }), 400

    with db_cursor(dictionary=False) as (conn, cur):
        asignaciones = ["agenda_publica = %s", "presentacion_publica = %s"]
        valores = [1 if activar else 0, presentacion]

        for campo in CAMPOS_REQUERIDOS:
            if datos.get(campo) is not None:
                asignaciones.append(f"{campo} = %s")
                valores.append((datos.get(campo) or "").strip() or None)

        cur.execute(
            f"UPDATE usuarios SET {', '.join(asignaciones)} WHERE id = %s",
            (*valores, current_user.id),
        )
        conn.commit()

    # El directorio se rehace entero para este consultorio. Apagar la agenda de
    # alguien tiene que sacarlo de la busqueda en el acto: si se quedara
    # figurando, seguiria recibiendo turnos que decidio no aceptar.
    publicados = None
    cliente = cliente_actual()
    if cliente is not None:
        from app import reservas

        publicados = reservas.sincronizar_directorio(cliente)

    return jsonify({
        "activa": activar,
        "mensaje": (
            "Ya podes recibir turnos online." if activar
            else "Dejaste de aparecer en la busqueda de pacientes."
        ),
        "publicados_en_el_consultorio": publicados,
    })
