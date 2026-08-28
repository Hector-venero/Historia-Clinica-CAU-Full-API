"""Comunicados internos: avisos que la conduccion publica para todo el equipo.

Los lee cualquier usuario autenticado; solo director y administrativo publican
o borran. Es el unico modulo del bloque de comunicacion que no depende de los
grupos profesionales, por eso se incorpora por separado.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.database import db_cursor
from app.utils.mails_comunicados import enviar_aviso_comunicado
from app.utils.permisos import requiere_rol, requiere_modulo

bp_comunicados = Blueprint("comunicados", __name__)

ROLES_PUBLICADORES = ("director", "administrativo")

# `normal` llega solo por la campana; `importante` ademas por mail. Se valida
# aca y no con un ENUM en la base: ampliar un ENUM en uso obliga a reescribir la
# tabla, y un valor invalido daria un 1265 en vez de un error legible.
PRIORIDADES = ("normal", "importante")
PRIORIDAD_POR_DEFECTO = "normal"


@bp_comunicados.route("/api/comunicados", methods=["GET"])
@login_required
@requiere_modulo('comunicados')
def listar_comunicados():
    with db_cursor() as (_conn, cursor):
        cursor.execute("""
            SELECT
                c.id,
                c.titulo,
                c.contenido,
                c.autor_id,
                c.creado_en,
                c.actualizado_en,
                c.prioridad,
                u.nombre AS autor_nombre,
                u.rol AS autor_rol,
                -- LEFT JOIN y no una subconsulta por fila: el estado de leido
                -- es por usuario y la ausencia de fila significa no leido.
                l.id IS NOT NULL AS leido
            FROM comunicados c
            JOIN usuarios u ON u.id = c.autor_id
            LEFT JOIN comunicado_lecturas l
                   ON l.comunicado_id = c.id AND l.usuario_id = %s
            ORDER BY c.creado_en DESC
        """, (current_user.id,))
        comunicados = cursor.fetchall()

    # Se informa por fila para que la UI sepa si mostrar el boton de borrar.
    # Es solo presentacion: el permiso real lo aplica @requiere_rol en el DELETE.
    puede_eliminar = current_user.rol in ROLES_PUBLICADORES
    for comunicado in comunicados:
        comunicado["puede_eliminar"] = puede_eliminar
        # MySQL devuelve el resultado de `IS NOT NULL` como 1/0; el frontend lo
        # usa para resaltar, asi que conviene entregarlo ya como booleano.
        comunicado["leido"] = bool(comunicado.get("leido"))

    return jsonify(comunicados)


@bp_comunicados.route("/api/comunicados", methods=["POST"])
@login_required
@requiere_modulo('comunicados')
@requiere_rol(*ROLES_PUBLICADORES)
def crear_comunicado():
    data = request.get_json(silent=True) or {}
    titulo = (data.get("titulo") or "").strip()
    contenido = (data.get("contenido") or "").strip()

    prioridad = (data.get("prioridad") or PRIORIDAD_POR_DEFECTO).strip().lower()

    if not titulo:
        return jsonify({"error": "El título es obligatorio"}), 400
    if not contenido:
        return jsonify({"error": "El contenido es obligatorio"}), 400
    if prioridad not in PRIORIDADES:
        return jsonify({"error": f"prioridad debe ser {' o '.join(PRIORIDADES)}"}), 400

    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute(
            "INSERT INTO comunicados (titulo, contenido, autor_id, prioridad) VALUES (%s, %s, %s, %s)",
            (titulo, contenido, current_user.id, prioridad),
        )
        conn.commit()
        comunicado_id = cursor.lastrowid

        # Quien publica ya lo leyo: sin esto el autor ve su propio aviso como no
        # leido y el contador le queda en 1 apenas termina de publicarlo.
        cursor.execute(
            "INSERT IGNORE INTO comunicado_lecturas (comunicado_id, usuario_id) VALUES (%s, %s)",
            (comunicado_id, current_user.id),
        )
        conn.commit()

        destinatarios = []
        if prioridad == "importante":
            # Solo activos: un usuario dado de baja no deberia seguir recibiendo
            # comunicaciones internas.
            cursor.execute(
                "SELECT email FROM usuarios WHERE activo = 1 AND email IS NOT NULL AND email <> '' AND id <> %s",
                (current_user.id,),
            )
            destinatarios = [fila[0] for fila in cursor.fetchall()]

    # Fuera del `with`: el envio es en segundo plano y no tiene por que retener
    # la conexion a la base mientras se arma el mensaje.
    if destinatarios:
        enviar_aviso_comunicado(destinatarios, titulo, contenido, current_user.nombre)

    return jsonify({
        "message": "Comunicado publicado",
        "id": comunicado_id,
        "prioridad": prioridad,
        "avisados": len(destinatarios),
    }), 201


@bp_comunicados.route("/api/comunicados/no_leidos", methods=["GET"])
@login_required
@requiere_modulo('comunicados')
def contar_no_leidos():
    """Cantidad para el globo de la campana. La consulta la hace cada carga de
    la barra superior, por eso devuelve solo el numero y no las filas."""
    with db_cursor() as (_conn, cursor):
        cursor.execute("""
            SELECT COUNT(*) AS cantidad
            FROM comunicados c
            LEFT JOIN comunicado_lecturas l
                   ON l.comunicado_id = c.id AND l.usuario_id = %s
            WHERE l.id IS NULL
        """, (current_user.id,))
        fila = cursor.fetchone()

    return jsonify({"cantidad": (fila or {}).get("cantidad", 0)})


@bp_comunicados.route("/api/comunicados/<int:comunicado_id>/leer", methods=["POST"])
@login_required
@requiere_modulo('comunicados')
def marcar_leido(comunicado_id):
    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute("SELECT id FROM comunicados WHERE id = %s", (comunicado_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Comunicado no encontrado"}), 404

        # INSERT IGNORE contra el UNIQUE (comunicado_id, usuario_id): marcar dos
        # veces lo mismo no es un error, y evita consultar antes de escribir.
        cursor.execute(
            "INSERT IGNORE INTO comunicado_lecturas (comunicado_id, usuario_id) VALUES (%s, %s)",
            (comunicado_id, current_user.id),
        )
        conn.commit()

    return jsonify({"message": "Comunicado marcado como leído"})


@bp_comunicados.route("/api/comunicados/leer_todos", methods=["POST"])
@login_required
@requiere_modulo('comunicados')
def marcar_todos_leidos():
    with db_cursor(dictionary=False) as (conn, cursor):
        # Un solo INSERT ... SELECT en vez de una fila por vez: al entrar por
        # primera vez puede haber que marcar todo el historico.
        cursor.execute("""
            INSERT IGNORE INTO comunicado_lecturas (comunicado_id, usuario_id)
            SELECT c.id, %s FROM comunicados c
        """, (current_user.id,))
        conn.commit()
        marcados = cursor.rowcount

    return jsonify({"message": "Comunicados marcados como leídos", "marcados": marcados})


@bp_comunicados.route("/api/comunicados/<int:comunicado_id>", methods=["DELETE"])
@login_required
@requiere_modulo('comunicados')
@requiere_rol(*ROLES_PUBLICADORES)
def eliminar_comunicado(comunicado_id):
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id FROM comunicados WHERE id = %s", (comunicado_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Comunicado no encontrado"}), 404

        cursor.execute("DELETE FROM comunicados WHERE id = %s", (comunicado_id,))
        conn.commit()

    return jsonify({"message": "Comunicado eliminado"})
