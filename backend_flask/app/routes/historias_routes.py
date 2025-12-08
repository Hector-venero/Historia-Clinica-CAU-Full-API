# app/routes/historias_routes.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.database import get_connection
from app.utils.hashing import generar_hash
from app.utils.bfa_client import registrar_hash_en_bfa, verificar_hash_en_bfa
from app.utils.permisos import requiere_rol
from web3 import Web3
import hashlib, json

bp_historias = Blueprint("historias", __name__)

# =========================================================
#  Función auxiliar: Actualizar historia consolidada
# =========================================================
def actualizar_historia(paciente_id, usuario_id):
    """
    Genera o actualiza la historia consolidada del paciente
    sumando todas sus evoluciones y recalculando el hash local.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Obtener todas las evoluciones del paciente
    cursor.execute("""
        SELECT id, fecha, contenido, usuario_id
        FROM evoluciones
        WHERE paciente_id = %s
        ORDER BY fecha ASC
    """, (paciente_id,))
    evoluciones = cursor.fetchall()

    if not evoluciones:
        cursor.close()
        conn.close()
        return None  # no hay evoluciones todavía

    # 🧩 Convertir fechas a string (date o datetime) para evitar error JSON
    for evo in evoluciones:
        fecha_val = evo.get("fecha")
        evo["fecha"] = fecha_val.isoformat() if hasattr(fecha_val, "isoformat") else str(fecha_val)

    # 2️⃣ Generar resumen y hash
    resumen_json = json.dumps(evoluciones, sort_keys=True, ensure_ascii=False)
    hash_local = hashlib.sha256(resumen_json.encode()).hexdigest()

    # 3️⃣ Insertar o actualizar historia consolidada
    cursor.execute("""
        INSERT INTO historias (paciente_id, usuario_id, resumen, hash_local)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            usuario_id = VALUES(usuario_id),
            resumen = VALUES(resumen),
            hash_local = VALUES(hash_local),
            fecha = NOW();
    """, (paciente_id, usuario_id, resumen_json, hash_local))

    conn.commit()
    cursor.close()
    conn.close()
    return hash_local


# =========================================================
#  Crear nueva historia (manual o puntual)
# =========================================================
@bp_historias.route('/api/pacientes/<int:paciente_id>/historias', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def api_agregar_historia(paciente_id):
    """
    Recalcula la historia consolidada de un paciente sumando todas sus evoluciones.
    """
    hash_consolidado = actualizar_historia(paciente_id, current_user.id)

    if not hash_consolidado:
        return jsonify({"error": "El paciente no tiene evoluciones registradas"}), 400

    return jsonify({
        "message": "Historia actualizada automáticamente ✅",
        "hash_local": hash_consolidado
    }), 200


# =========================================================
#  Listar historias del paciente
# =========================================================
@bp_historias.route('/api/pacientes/<int:paciente_id>/historias', methods=['GET'])
@login_required
def api_get_historias(paciente_id):
    """
    Retorna todas las versiones de historia clínica de un paciente.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT h.*, u.nombre AS nombre_usuario
        FROM historias h
        JOIN usuarios u ON h.usuario_id = u.id
        WHERE h.paciente_id = %s
        ORDER BY h.fecha DESC
    """, (paciente_id,))
    historias = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(historias)