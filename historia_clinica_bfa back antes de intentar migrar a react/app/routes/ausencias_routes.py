# app/routes/ausencias_routes.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.permisos import requiere_rol
from datetime import datetime

bp_ausencias = Blueprint("ausencias", __name__)

# Crear una ausencia (bloqueo de agenda)
@bp_ausencias.route("/api/ausencias", methods=["POST"])
@login_required
@requiere_rol("director", "profesional", "administrativo")
def crear_ausencia():
    data = request.get_json(silent=True) or {}
    usuario_id = data.get("usuario_id") or current_user.id
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    motivo = data.get("motivo", "")

    if not fecha_inicio or not fecha_fin:
        return jsonify({"error": "Se requieren fecha_inicio y fecha_fin"}), 400

    # Restricción: un médico solo puede crear ausencias para sí mismo
    if current_user.rol == "profesional" and usuario_id != current_user.id:
        return jsonify({"error": "No puede bloquear agenda de otros profesionales"}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ausencias (usuario_id, fecha_inicio, fecha_fin, motivo, creado_por)
        VALUES (%s, %s, %s, %s, %s)
    """, (usuario_id, fecha_inicio, fecha_fin, motivo, current_user.id))
    conn.commit()
    ausencia_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({"message": "Ausencia registrada ✅", "id": ausencia_id}), 201


# Listar ausencias (un médico solo ve las suyas, admin/director ven todas)
@bp_ausencias.route("/api/ausencias", methods=["GET"])
@login_required
@requiere_rol("director", "profesional", "administrativo")
def listar_ausencias():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if current_user.rol == "profesional":
        cursor.execute("""
            SELECT a.*, u.nombre AS nombre_usuario
            FROM ausencias a
            JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.usuario_id = %s
            ORDER BY fecha_inicio
        """, (current_user.id,))
    else:
        cursor.execute("""
            SELECT a.*, u.nombre AS nombre_usuario
            FROM ausencias a
            JOIN usuarios u ON a.usuario_id = u.id
            ORDER BY fecha_inicio
        """)
    
    ausencias = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(ausencias)


# Eliminar una ausencia (soft delete opcional, acá lo hago hard delete simple)
@bp_ausencias.route("/api/ausencias/<int:ausencia_id>", methods=["DELETE"])
@login_required
@requiere_rol("director", "profesional", "administrativo")
def eliminar_ausencia(ausencia_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM ausencias WHERE id=%s", (ausencia_id,))
    ausencia = cursor.fetchone()
    if not ausencia:
        cursor.close(); conn.close()
        return jsonify({"error": "Ausencia no encontrada"}), 404

    # Restricción: un médico solo puede eliminar sus propias ausencias
    if current_user.rol == "profesional" and ausencia["usuario_id"] != current_user.id:
        cursor.close(); conn.close()
        return jsonify({"error": "No autorizado"}), 403

    cursor.execute("DELETE FROM ausencias WHERE id=%s", (ausencia_id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Ausencia eliminada ✅"})
