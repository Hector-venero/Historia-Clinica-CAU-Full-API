# app/routes/historias_routes.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.database import get_connection
from app.utils.hashing import generar_hash
from app.utils.bfa_client import registrar_hash_en_bfa
from app.utils.permisos import requiere_rol
import hashlib, json

bp_historias = Blueprint("historias", __name__)

# =========================================================
# 🧩 Función auxiliar: Actualizar historia consolidada
# =========================================================
def actualizar_historia(paciente_id, usuario_id):
    """Genera o actualiza la historia consolidada del paciente
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
        if hasattr(fecha_val, "isoformat"):
            evo["fecha"] = fecha_val.isoformat()
        else:
            evo["fecha"] = str(fecha_val)

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
# 🩺 Crear nueva historia (manual o puntual)
# =========================================================
@bp_historias.route('/api/pacientes/<int:paciente_id>/historias', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def api_agregar_historia(paciente_id):
    # ⚙️ Recalcular historia consolidada desde evoluciones
    hash_consolidado = actualizar_historia(paciente_id, current_user.id)

    if not hash_consolidado:
        return jsonify({"error": "El paciente no tiene evoluciones registradas"}), 400

    return jsonify({
        "message": "Historia actualizada automáticamente ✅",
        "hash_local": hash_consolidado
    }), 200

# =========================================================
# 📄 Listar historias del paciente
# =========================================================
@bp_historias.route('/api/pacientes/<int:paciente_id>/historias', methods=['GET'])
@login_required
def api_get_historias(paciente_id):
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

# =========================================================
# 🔗 Verificar integridad de la historia con Blockchain BFA
# =========================================================
@bp_historias.route('/api/pacientes/<int:paciente_id>/historia/verificar', methods=['GET'])
@login_required
def verificar_historia_blockchain(paciente_id):
    """Compara el hash local de la historia clínica consolidada con el registrado en BFA."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Obtener la última historia consolidada
    cursor.execute("""
        SELECT id, hash_local, hash_bfa, fecha
        FROM historias
        WHERE paciente_id = %s
        ORDER BY fecha DESC
        LIMIT 1
    """, (paciente_id,))
    historia = cursor.fetchone()
    cursor.close()
    conn.close()

    if not historia:
        return jsonify({"error": "No existe historia consolidada para este paciente"}), 404

    hash_local = historia["hash_local"]
    hash_bfa = historia.get("hash_bfa")

    # 2️⃣ Verificar contra la BFA
    try:
        from app.utils.bfa_client import verificar_hash_en_bfa
        hash_en_bfa = verificar_hash_en_bfa(hash_local)
    except Exception as e:
        return jsonify({"error": f"No se pudo verificar en BFA: {str(e)}"}), 500

    # 3️⃣ Comparar y devolver resultado
    estado = "válido" if hash_en_bfa == hash_local else "inconsistente"

    return jsonify({
        "paciente_id": paciente_id,
        "hash_local": hash_local,
        "hash_bfa": hash_en_bfa,
        "estado": estado,
        "fecha": historia["fecha"]
    })
