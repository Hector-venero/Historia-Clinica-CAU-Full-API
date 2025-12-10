from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.permisos import requiere_rol
from datetime import datetime, timedelta

bp_disponibilidades = Blueprint("disponibilidades", __name__)

# ==========================================================
# 📅 CRUD de Disponibilidades de los Médicos
# ==========================================================

DIAS_ORDENADOS = [
    "Lunes", "Martes", "Miercoles",
    "Jueves", "Viernes", "Sabado", "Domingo"
]
orden_sql = ",".join([f"'{d}'" for d in DIAS_ORDENADOS])


def normalizar_dia(dia):
    mapa = {
        "lunes": "Lunes",
        "martes": "Martes",
        "miercoles": "Miercoles",
        "miércoles": "Miercoles",
        "jueves": "Jueves",
        "viernes": "Viernes",
        "sabado": "Sabado",
        "sábado": "Sabado",
        "domingo": "Domingo"
    }
    return mapa.get(dia.lower().strip())


# ==========================================================
# GET — Listar disponibilidades
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def listar_disponibilidades():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if current_user.rol == 'profesional':
        cursor.execute(f"""
            SELECT id, usuario_id, dia_semana, hora_inicio, hora_fin, activo
            FROM disponibilidades
            WHERE usuario_id = %s
            ORDER BY FIELD(dia_semana, {orden_sql})
        """, (current_user.id,))
    else:
        cursor.execute(f"""
            SELECT d.id, d.usuario_id, u.nombre AS profesional,
                   d.dia_semana, d.hora_inicio, d.hora_fin, d.activo
            FROM disponibilidades d
            JOIN usuarios u ON d.usuario_id = u.id
            ORDER BY u.nombre ASC, FIELD(d.dia_semana, {orden_sql})
        """)

    disponibilidades = cursor.fetchall()
    cursor.close()
    conn.close()

    # 🟢 Normalizar resultados
    for d in disponibilidades:
        d["dia_semana"] = normalizar_dia(d["dia_semana"])  # para evitar acentos inconsistentes
        # convertir TIME → string
        if isinstance(d.get("hora_inicio"), timedelta):
            d["hora_inicio"] = (datetime.min + d["hora_inicio"]).time().strftime("%H:%M")
        if isinstance(d.get("hora_fin"), timedelta):
            d["hora_fin"] = (datetime.min + d["hora_fin"]).time().strftime("%H:%M")

    return jsonify(disponibilidades)


# ==========================================================
# POST — Crear disponibilidad
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional')
def crear_disponibilidad():

    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    usuario_id = current_user.id
    dia_semana = normalizar_dia(data.get("dia_semana", ""))
    hora_inicio = data.get("hora_inicio")
    hora_fin = data.get("hora_fin")
    activo = data.get("activo", True)

    if not dia_semana:
        return jsonify({"error": "Día inválido"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        INSERT INTO disponibilidades (usuario_id, dia_semana, hora_inicio, hora_fin, activo)
        VALUES (%s, %s, %s, %s, %s)
    """, (usuario_id, dia_semana, hora_inicio, hora_fin, activo))

    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({"id": new_id, "message": "Disponibilidad creada correctamente"}), 201


# ==========================================================
# PUT — Actualizar disponibilidad (solo horas y activo)
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades/<int:id>', methods=['PUT'])
@login_required
@requiere_rol('director', 'profesional')
def editar_disponibilidad(id):

    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM disponibilidades WHERE id=%s", (id,))
    disp = cursor.fetchone()
    if not disp:
        cursor.close(); conn.close()
        return jsonify({"error": "Disponibilidad no encontrada"}), 404

    if current_user.rol == 'profesional' and disp["usuario_id"] != current_user.id:
        cursor.close(); conn.close()
        return jsonify({"error": "No autorizado"}), 403

    hora_inicio = data.get("hora_inicio")
    hora_fin = data.get("hora_fin")
    activo = data.get("activo")

    cursor.execute("""
        UPDATE disponibilidades
        SET hora_inicio=%s, hora_fin=%s, activo=%s
        WHERE id=%s
    """, (hora_inicio, hora_fin, activo, id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Disponibilidad actualizada correctamente"})


# ==========================================================
# DELETE
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades/<int:id>', methods=['DELETE'])
@login_required
@requiere_rol('director', 'profesional')
def eliminar_disponibilidad(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM disponibilidades WHERE id=%s", (id,))
    disp = cursor.fetchone()

    if not disp:
        cursor.close(); conn.close()
        return jsonify({"error": "Disponibilidad no encontrada"}), 404

    if current_user.rol == 'profesional' and disp["usuario_id"] != current_user.id:
        cursor.close(); conn.close()
        return jsonify({"error": "No autorizado"}), 403

    cursor.execute("DELETE FROM disponibilidades WHERE id=%s", (id,))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify({"message": "Disponibilidad eliminada correctamente"})
