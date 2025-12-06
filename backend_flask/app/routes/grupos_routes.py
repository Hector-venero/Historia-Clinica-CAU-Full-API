from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.permisos import requiere_rol

bp_grupos = Blueprint("grupos", __name__)

# =====================================================
# 📋 Obtener todos los grupos profesionales
# =====================================================
@bp_grupos.route("/api/grupos", methods=["GET"])
@login_required
def obtener_grupos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, nombre, descripcion, color
        FROM grupos_profesionales
        ORDER BY nombre ASC
    """)
    grupos = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(grupos)


# =====================================================
# 🔹 Obtener un grupo por ID
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>", methods=["GET"])
@login_required
def obtener_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, nombre, descripcion, color
        FROM grupos_profesionales
        WHERE id = %s
    """, (grupo_id,))
    grupo = cursor.fetchone()
    cursor.close()
    conn.close()

    if not grupo:
        return jsonify({"error": "Grupo no encontrado"}), 404

    return jsonify(grupo)


# =====================================================
# 👥 Obtener los miembros de un grupo
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>/miembros", methods=["GET"])
@login_required
def obtener_miembros(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id, u.nombre, u.rol
        FROM grupo_miembros gm
        JOIN usuarios u ON gm.usuario_id = u.id
        WHERE gm.grupo_id = %s
    """, (grupo_id,))
    miembros = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(miembros)


# =====================================================
# ➕ Crear un nuevo grupo (solo director)
# =====================================================
@bp_grupos.route("/api/grupos", methods=["POST"])
@login_required
@requiere_rol("director")
def crear_grupo():
    data = request.get_json()
    nombre = data.get("nombre")
    descripcion = data.get("descripcion")
    color = data.get("color", "#00936B")

    if not nombre:
        return jsonify({"error": "El nombre del grupo es obligatorio"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO grupos_profesionales (nombre, descripcion, color)
        VALUES (%s, %s, %s)
    """, (nombre, descripcion, color))
    conn.commit()
    grupo_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({"message": "Grupo creado correctamente", "id": grupo_id}), 201


# =====================================================
# 📝 Editar grupo (solo director)
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>", methods=["PUT"])
@login_required
@requiere_rol("director")
def editar_grupo(grupo_id):
    data = request.get_json()
    nombre = data.get("nombre")
    descripcion = data.get("descripcion")
    color = data.get("color")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM grupos_profesionales WHERE id = %s", (grupo_id,))
    existe = cursor.fetchone()
    if not existe:
        cursor.close()
        conn.close()
        return jsonify({"error": "Grupo no encontrado"}), 404

    cursor.execute("""
        UPDATE grupos_profesionales
        SET nombre = %s, descripcion = %s, color = %s
        WHERE id = %s
    """, (nombre, descripcion, color, grupo_id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Grupo actualizado correctamente"})


# =====================================================
# ❌ Eliminar grupo (solo director)
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>", methods=["DELETE"])
@login_required
@requiere_rol("director")
def eliminar_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Verificar existencia
    cursor.execute("SELECT id FROM grupos_profesionales WHERE id = %s", (grupo_id,))
    existe = cursor.fetchone()
    if not existe:
        cursor.close()
        conn.close()
        return jsonify({"error": "Grupo no encontrado"}), 404

    # Borrar miembros primero (FK)
    cursor.execute("DELETE FROM grupo_miembros WHERE grupo_id = %s", (grupo_id,))

    # Borrar grupo
    cursor.execute("DELETE FROM grupos_profesionales WHERE id = %s", (grupo_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Grupo eliminado correctamente"})


# =====================================================
# 👤 Agregar un miembro a un grupo (solo director)
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>/miembros", methods=["POST"])
@login_required
@requiere_rol("director")
def agregar_miembro(grupo_id):
    data = request.get_json()
    usuario_id = data.get("usuario_id")

    if not usuario_id:
        return jsonify({"error": "Falta el ID del usuario"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO grupo_miembros (grupo_id, usuario_id)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE usuario_id = usuario_id
    """, (grupo_id, usuario_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Miembro agregado correctamente"}), 201


# =====================================================
# ❌ Quitar un miembro (solo director)
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>/miembros/<int:usuario_id>", methods=["DELETE"])
@login_required
@requiere_rol("director")
def quitar_miembro(grupo_id, usuario_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM grupo_miembros
        WHERE grupo_id = %s AND usuario_id = %s
    """, (grupo_id, usuario_id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Miembro eliminado correctamente"})
