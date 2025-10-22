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
        ON DUPLICATE KEY UPDATE grupo_id = grupo_id
    """, (grupo_id, usuario_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Miembro agregado correctamente"}), 201


# =====================================================
# 📅 Obtener turnos de todos los miembros de un grupo profesional
# =====================================================
@bp_grupos.route("/api/turnos/grupo/<int:grupo_id>", methods=["GET"])
@login_required
@requiere_rol("director", "profesional", "administrativo")
def turnos_por_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            t.id,
            t.fecha,
            t.motivo,
            p.nombre AS paciente,
            p.dni,
            u.nombre AS profesional,
            gp.color
        FROM turnos t
        JOIN pacientes p ON t.paciente_id = p.id
        JOIN usuarios u ON t.usuario_id = u.id
        JOIN grupo_miembros gm ON gm.usuario_id = u.id
        JOIN grupos_profesionales gp ON gp.id = gm.grupo_id
        WHERE gm.grupo_id = %s
        ORDER BY t.fecha ASC
    """, (grupo_id,))

    turnos = cursor.fetchall()
    cursor.close()
    conn.close()

    eventos = []
    for t in turnos:
        fecha = t["fecha"]
        # Asegurar formato ISO con "T"
        if hasattr(fecha, "isoformat"):
            fecha_str = fecha.isoformat()
        else:
            fecha_str = str(fecha).replace(" ", "T")

        eventos.append({
            "id": t["id"],
            "paciente": t["paciente"],
            "dni": t["dni"],
            "start": fecha_str,
            "description": t["motivo"],
            "profesional": t["profesional"],
            "color": t["color"]
        })

    return jsonify(eventos)

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
