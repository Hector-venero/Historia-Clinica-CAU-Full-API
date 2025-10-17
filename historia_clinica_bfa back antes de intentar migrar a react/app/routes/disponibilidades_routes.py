from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.permisos import requiere_rol
from datetime import datetime, timedelta

bp_disponibilidades = Blueprint("disponibilidades", __name__)

# ==========================================================
# 📅 CRUD de Disponibilidades de los Médicos
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def listar_disponibilidades():
    """Devuelve todas las disponibilidades registradas.
       Los profesionales solo ven las suyas propias."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if current_user.rol == 'profesional':
        cursor.execute("""
            SELECT d.id, d.dia_semana, d.hora_inicio, d.hora_fin, d.activo
            FROM disponibilidades d
            WHERE d.usuario_id = %s
            ORDER BY FIELD(d.dia_semana, 
                'Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo')
        """, (current_user.id,))
    else:
        cursor.execute("""
            SELECT d.id, d.usuario_id, u.nombre AS profesional,
                   d.dia_semana, d.hora_inicio, d.hora_fin, d.activo
            FROM disponibilidades d
            JOIN usuarios u ON d.usuario_id = u.id
            ORDER BY u.nombre ASC, FIELD(d.dia_semana, 
                'Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo')
        """)

    disponibilidades = cursor.fetchall()
    cursor.close()
    conn.close()
    # Convertir los campos TIME a string
    for d in disponibilidades:
        if isinstance(d.get("hora_inicio"), timedelta):
            d["hora_inicio"] = (datetime.min + d["hora_inicio"]).time().strftime("%H:%M")
        if isinstance(d.get("hora_fin"), timedelta):
            d["hora_fin"] = (datetime.min + d["hora_fin"]).time().strftime("%H:%M")

    return jsonify(disponibilidades)

@bp_disponibilidades.route('/api/disponibilidades', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional')
def crear_disponibilidad():
    """Crea una nueva franja horaria disponible para un médico."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    usuario_id = data.get("usuario_id") or current_user.id
    dia_input = data.get("dia_semana", "").strip()
    hora_inicio = data.get("hora_inicio")
    hora_fin = data.get("hora_fin")
    activo = data.get("activo", True)

    mapa_dias = {
        "lunes": "Lunes",
        "martes": "Martes",
        "miercoles": "Miercoles",
        "miércoles": "Miercoles",
        "jueves": "Jueves",
        "viernes": "Viernes",
        "sabado": "Sabado",
        "sábado": "Sabado"
    }

    dia_semana = mapa_dias.get(dia_input.lower().strip())
    if not dia_semana:
        print(f"❌ Día inválido recibido: {dia_input}")
        return jsonify({"error": f"Día inválido: {dia_input}"}), 400
    else:
        print(f"📅 Día recibido: {dia_input} → Normalizado: {dia_semana}")

    # Un profesional solo puede crear su propia disponibilidad
    if current_user.rol == 'profesional' and usuario_id != current_user.id:
        return jsonify({"error": "No autorizado para crear disponibilidad de otro usuario"}), 403

    if not (dia_semana and hora_inicio and hora_fin):
        return jsonify({"error": "Campos obligatorios faltantes"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        INSERT INTO disponibilidades (usuario_id, dia_semana, hora_inicio, hora_fin, activo)
        VALUES (%s, %s, %s, %s, %s)
    """, (usuario_id, dia_semana, hora_inicio, hora_fin, activo))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify({"message": "Disponibilidad creada correctamente ✅"}), 201

@bp_disponibilidades.route('/api/disponibilidades/<int:id>', methods=['PUT'])
@login_required
@requiere_rol('director', 'profesional')
def editar_disponibilidad(id):
    """Edita una franja horaria existente."""
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

    # Un profesional solo puede editar su propia disponibilidad
    if current_user.rol == 'profesional' and disp['usuario_id'] != current_user.id:
        cursor.close(); conn.close()
        return jsonify({"error": "No autorizado"}), 403

    dia_semana = data.get("dia_semana")
    hora_inicio = data.get("hora_inicio")
    hora_fin = data.get("hora_fin")
    activo = data.get("activo", True)

    cursor.execute("""
        UPDATE disponibilidades
        SET dia_semana=%s, hora_inicio=%s, hora_fin=%s, activo=%s
        WHERE id=%s
    """, (dia_semana, hora_inicio, hora_fin, activo, id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Disponibilidad actualizada correctamente ✅"})


@bp_disponibilidades.route('/api/disponibilidades/<int:id>', methods=['DELETE'])
@login_required
@requiere_rol('director', 'profesional')
def eliminar_disponibilidad(id):
    """Elimina una franja horaria de disponibilidad."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM disponibilidades WHERE id=%s", (id,))
    disp = cursor.fetchone()
    if not disp:
        cursor.close(); conn.close()
        return jsonify({"error": "Disponibilidad no encontrada"}), 404

    if current_user.rol == 'profesional' and disp['usuario_id'] != current_user.id:
        cursor.close(); conn.close()
        return jsonify({"error": "No autorizado"}), 403

    cursor.execute("DELETE FROM disponibilidades WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Disponibilidad eliminada correctamente ✅"})
