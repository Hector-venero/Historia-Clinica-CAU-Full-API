# app/routes/blockchain_routes.py

from flask import Blueprint, jsonify
from flask_login import login_required
from app.utils.hashing import generar_hash
from app.database import get_connection

bp_blockchain = Blueprint("blockchain", __name__)

@bp_blockchain.route("/api/blockchain/verificar/<int:historia_id>", methods=["GET"])
@login_required
def verificar_historia(historia_id):
    """
    Verifica la integridad de una historia clínica:
    - Recupera datos de la DB
    - Recalcula el hash local
    - Compara con el hash guardado
    - Devuelve estado y tx_hash de blockchain
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()
    cursor.close()
    conn.close()

    if not historia:
        return jsonify({"error": "Historia no encontrada"}), 404

    # 🔹 Recalcular hash local
    contenido = (
        (historia['motivo_consulta'] or '') +
        (historia['antecedentes'] or '') +
        (historia['examen_fisico'] or '') +
        (historia['diagnostico'] or '') +
        (historia['tratamiento'] or '') +
        (historia['observaciones'] or '')
    )
    hash_actual = generar_hash(contenido)
    es_valido = (hash_actual == historia["hash"])

    return jsonify({
        "historia_id": historia_id,
        "hash_guardado": historia["hash"],
        "hash_recalculado": hash_actual,
        "valido": es_valido,
        "tx_hash": historia["tx_hash"]
    })
