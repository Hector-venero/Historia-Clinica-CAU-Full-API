"""Comunicados internos: avisos que la conduccion publica para todo el equipo.

Los lee cualquier usuario autenticado; solo director y administrativo publican
o borran. Es el unico modulo del bloque de comunicacion que no depende de los
grupos profesionales, por eso se incorpora por separado.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.database import db_cursor
from app.utils.permisos import requiere_rol

bp_comunicados = Blueprint("comunicados", __name__)

ROLES_PUBLICADORES = ("director", "administrativo")


@bp_comunicados.route("/api/comunicados", methods=["GET"])
@login_required
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
                u.nombre AS autor_nombre,
                u.rol AS autor_rol
            FROM comunicados c
            JOIN usuarios u ON u.id = c.autor_id
            ORDER BY c.creado_en DESC
        """)
        comunicados = cursor.fetchall()

    # Se informa por fila para que la UI sepa si mostrar el boton de borrar.
    # Es solo presentacion: el permiso real lo aplica @requiere_rol en el DELETE.
    puede_eliminar = current_user.rol in ROLES_PUBLICADORES
    for comunicado in comunicados:
        comunicado["puede_eliminar"] = puede_eliminar

    return jsonify(comunicados)


@bp_comunicados.route("/api/comunicados", methods=["POST"])
@login_required
@requiere_rol(*ROLES_PUBLICADORES)
def crear_comunicado():
    data = request.get_json(silent=True) or {}
    titulo = (data.get("titulo") or "").strip()
    contenido = (data.get("contenido") or "").strip()

    if not titulo:
        return jsonify({"error": "El título es obligatorio"}), 400
    if not contenido:
        return jsonify({"error": "El contenido es obligatorio"}), 400

    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute(
            "INSERT INTO comunicados (titulo, contenido, autor_id) VALUES (%s, %s, %s)",
            (titulo, contenido, current_user.id),
        )
        conn.commit()
        comunicado_id = cursor.lastrowid

    return jsonify({"message": "Comunicado publicado", "id": comunicado_id}), 201


@bp_comunicados.route("/api/comunicados/<int:comunicado_id>", methods=["DELETE"])
@login_required
@requiere_rol(*ROLES_PUBLICADORES)
def eliminar_comunicado(comunicado_id):
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id FROM comunicados WHERE id = %s", (comunicado_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Comunicado no encontrado"}), 404

        cursor.execute("DELETE FROM comunicados WHERE id = %s", (comunicado_id,))
        conn.commit()

    return jsonify({"message": "Comunicado eliminado"})
