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

    # (Opcional) Traer miembros para mostrar en la lista
    for g in grupos:
        cursor.execute("""
            SELECT u.id, u.nombre, u.rol
            FROM grupo_miembros gm
            JOIN usuarios u ON gm.usuario_id = u.id
            WHERE gm.grupo_id = %s
        """, (g["id"],))
        g["miembros"] = cursor.fetchall()

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

    if not grupo:
        cursor.close(); conn.close()
        return jsonify({"error": "Grupo no encontrado"}), 404

    # Traer miembros
    cursor.execute("""
        SELECT u.id, u.nombre, u.rol
        FROM grupo_miembros gm
        JOIN usuarios u ON gm.usuario_id = u.id
        WHERE gm.grupo_id = %s
    """, (grupo_id,))
    grupo["miembros"] = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(grupo)


# =====================================================
# ➕ Crear un nuevo grupo (solo director)
# =====================================================
@bp_grupos.route("/api/grupos", methods=["POST"])
@login_required
@requiere_rol("director")
def crear_grupo():
    data = request.get_json()
    nombre = data.get("nombre")
    descripcion = data.get("descripcion", "")
    color = data.get("color", "#00936B")
    miembros_ids = data.get("miembros", []) # Lista de IDs

    if not nombre:
        return jsonify({"error": "El nombre del grupo es obligatorio"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Crear el grupo
        cursor.execute("""
            INSERT INTO grupos_profesionales (nombre, descripcion, color)
            VALUES (%s, %s, %s)
        """, (nombre, descripcion, color))
        grupo_id = cursor.lastrowid

        # 2. Agregar miembros (con validación de rol)
        if miembros_ids:
            format_strings = ','.join(['%s'] * len(miembros_ids))
            cursor.execute(f"SELECT id, rol FROM usuarios WHERE id IN ({format_strings})", tuple(miembros_ids))
            usuarios_db = cursor.fetchall()
            
            # Filtramos solo profesionales y areas
            # 👇 AQUÍ ESTÁ LA VALIDACIÓN IMPORTANTE
            validos = [u[0] for u in usuarios_db if u[1] in ['profesional', 'area']]
            
            if validos:
                values = [(grupo_id, uid) for uid in validos]
                cursor.executemany("INSERT INTO grupo_miembros (grupo_id, usuario_id) VALUES (%s, %s)", values)

        conn.commit()
        return jsonify({"message": "Grupo creado correctamente", "id": grupo_id}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


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
    miembros_ids = data.get("miembros") # Puede ser None

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Actualizar datos básicos
        if nombre:
            cursor.execute("UPDATE grupos_profesionales SET nombre=%s WHERE id=%s", (nombre, grupo_id))
        if descripcion is not None:
            cursor.execute("UPDATE grupos_profesionales SET descripcion=%s WHERE id=%s", (descripcion, grupo_id))
        if color:
            cursor.execute("UPDATE grupos_profesionales SET color=%s WHERE id=%s", (color, grupo_id))

        # Actualizar miembros
        if miembros_ids is not None:
            cursor.execute("DELETE FROM grupo_miembros WHERE grupo_id=%s", (grupo_id,))
            
            if miembros_ids:
                format_strings = ','.join(['%s'] * len(miembros_ids))
                cursor.execute(f"SELECT id, rol FROM usuarios WHERE id IN ({format_strings})", tuple(miembros_ids))
                usuarios_db = cursor.fetchall()
                
                # 👇 VALIDACIÓN
                validos = [u[0] for u in usuarios_db if u[1] in ['profesional', 'area']]

                if validos:
                    values = [(grupo_id, uid) for uid in validos]
                    cursor.executemany("INSERT INTO grupo_miembros (grupo_id, usuario_id) VALUES (%s, %s)", values)

        conn.commit()
        return jsonify({"message": "Grupo actualizado correctamente"})

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# =====================================================
# ❌ Eliminar grupo (solo director)
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>", methods=["DELETE"])
@login_required
@requiere_rol("director")
def eliminar_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM grupos_profesionales WHERE id = %s", (grupo_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Grupo eliminado correctamente"})


# =====================================================
# 👤 Agregar un miembro a un grupo (Endpoint individual)
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

    # 👇 VALIDACIÓN INDIVIDUAL
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
    usuario = cursor.fetchone()
    
    if not usuario:
        cursor.close(); conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    if usuario[0] not in ['profesional', 'area']:
        cursor.close(); conn.close()
        return jsonify({"error": "Solo se pueden agregar profesionales o áreas a los grupos"}), 400

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
# ❌ Quitar un miembro
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>/miembros/<int:usuario_id>", methods=["DELETE"])
@login_required
@requiere_rol("director")
def quitar_miembro(grupo_id, usuario_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM grupo_miembros WHERE grupo_id = %s AND usuario_id = %s", (grupo_id, usuario_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Miembro eliminado correctamente"})

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