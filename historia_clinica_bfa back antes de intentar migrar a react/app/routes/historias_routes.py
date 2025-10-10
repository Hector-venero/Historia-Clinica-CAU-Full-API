# app/routes/historias_routes.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.database import get_connection
from app.utils.hashing import generar_hash
from app.utils.blockchain import publicar_hash_en_bfa
from app.utils.permisos import requiere_rol

bp_historias = Blueprint("historias", __name__)

@bp_historias.route('/api/pacientes/<int:paciente_id>/historias', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def api_agregar_historia(paciente_id):
    data = request.json or {}

    motivo = data.get('motivo_consulta', '').strip()
    antecedentes = data.get('antecedentes', '').strip()
    examen_fisico = data.get('examen_fisico', '').strip()
    diagnostico = data.get('diagnostico', '').strip()
    tratamiento = data.get('tratamiento', '').strip()
    observaciones = data.get('observaciones', '').strip()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 🔹 Generar hash local
    contenido = f"{paciente_id}|{motivo}|{antecedentes}|{examen_fisico}|{diagnostico}|{tratamiento}|{observaciones}"
    hash_hex = generar_hash(contenido)

    # 🔹 Publicar en BFA
    try:
        tx_hash = publicar_hash_en_bfa(hash_hex)
    except Exception as e:
        tx_hash = None
        print(f"⚠️ Error publicando hash en BFA: {e}")

    # 🔹 Guardar en DB
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO historias (paciente_id, usuario_id, fecha, motivo_consulta, antecedentes,
                               examen_fisico, diagnostico, tratamiento, observaciones, hash, tx_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (paciente_id, current_user.id, fecha, motivo, antecedentes, examen_fisico,
          diagnostico, tratamiento, observaciones, hash_hex, tx_hash))
    conn.commit()
    historia_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({
        "message": "Historia guardada ✅",
        "id": historia_id,
        "hash": hash_hex,
        "tx_hash": tx_hash
    }), 201


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
