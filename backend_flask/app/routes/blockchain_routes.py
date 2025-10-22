from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.utils.hashing import generar_hash, validar_integridad
from app.utils.bfa_client import registrar_hash_en_bfa
from app.database import get_connection
from web3 import Web3

bp_blockchain = Blueprint("blockchain", __name__)

# =============================================================
# 1️⃣ REGISTRAR HISTORIA EN LA BLOCKCHAIN BFA
# =============================================================
@bp_blockchain.route("/api/blockchain/registrar/<int:historia_id>", methods=["POST"])
@login_required
def registrar_en_bfa(historia_id):
    """
    Genera el hash de una historia clínica y lo publica en la Blockchain BFA.
    Guarda el hash y el tx_hash en la base de datos.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()

    if not historia:
        cursor.close()
        conn.close()
        return jsonify({"error": "Historia no encontrada"}), 404

    # 🔹 Generar contenido concatenado
    contenido = (
        (historia['motivo_consulta'] or '') +
        (historia['antecedentes'] or '') +
        (historia['examen_fisico'] or '') +
        (historia['diagnostico'] or '') +
        (historia['tratamiento'] or '') +
        (historia['observaciones'] or '')
    )

    # 🔹 Generar hash local
    hash_local = generar_hash(contenido)

    try:
        tx_hash = registrar_hash_en_bfa(hash_local)
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({"error": f"No se pudo publicar en la BFA: {str(e)}"}), 500

    # 🔹 Guardar en DB
    cursor.execute("""
        UPDATE historias
        SET hash = %s, tx_hash = %s
        WHERE id = %s
    """, (hash_local, tx_hash, historia_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "historia_id": historia_id,
        "hash": hash_local,
        "tx_hash": tx_hash,
        "mensaje": "✅ Hash publicado correctamente en la Blockchain BFA"
    }), 201


# =============================================================
# 2️⃣ VERIFICAR INTEGRIDAD DE UNA HISTORIA
# =============================================================
@bp_blockchain.route("/api/blockchain/verificar/<int:historia_id>", methods=["GET"])
@login_required
def verificar_historia(historia_id):
    """
    Verifica que el hash almacenado en la base de datos
    coincida con el registrado en la Blockchain BFA.
    """
    from app.utils.bfa_client import BFA_URL
    from web3 import Web3

    web3 = Web3(Web3.HTTPProvider(BFA_URL))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()
    cursor.close()
    conn.close()

    if not historia:
        return jsonify({"error": "Historia no encontrada"}), 404

    if not historia["tx_hash"]:
        return jsonify({"error": "La historia no tiene transacción registrada en BFA"}), 400

    # 🔹 Recalcular hash local
    contenido = (
        (historia['motivo_consulta'] or '') +
        (historia['antecedentes'] or '') +
        (historia['examen_fisico'] or '') +
        (historia['diagnostico'] or '') +
        (historia['tratamiento'] or '') +
        (historia['observaciones'] or '')
    )
    hash_local = generar_hash(contenido)

    # 🔹 Obtener hash publicado en BFA
    try:
        tx = web3.eth.get_transaction(historia["tx_hash"])
        hash_bfa = tx.input[2:]  # quitar prefijo '0x'
    except Exception as e:
        return jsonify({"error": f"No se pudo obtener transacción: {str(e)}"}), 500

    # 🔹 Comparar
    valido = (hash_local == hash_bfa)

    # 🔹 Registrar auditoría
    _registrar_auditoria(historia_id, hash_local, hash_bfa, valido, current_user.username)

    return jsonify({
        "historia_id": historia_id,
        "hash_local": hash_local,
        "hash_bfa": hash_bfa,
        "tx_hash": historia["tx_hash"],
        "valido": valido,
        "mensaje": "✅ Integridad verificada" if valido else "❌ La historia fue modificada"
    })


# =============================================================
# 3️⃣ LISTAR AUDITORÍAS (para administradores)
# =============================================================
@bp_blockchain.route("/api/blockchain/auditorias", methods=["GET"])
@login_required
def listar_auditorias():
    """
    Devuelve el historial de verificaciones realizadas (auditorías).
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM auditorias_blockchain ORDER BY fecha DESC")
    registros = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(registros)


# =============================================================
# 🔧 FUNCIÓN INTERNA: GUARDAR AUDITORÍA
# =============================================================
def _registrar_auditoria(historia_id, hash_local, hash_bfa, valido, usuario):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO auditorias_blockchain (historia_id, hash_local, hash_bfa, valido, usuario)
        VALUES (%s, %s, %s, %s, %s)
    """, (historia_id, hash_local, hash_bfa, int(valido), usuario))
    conn.commit()
    cursor.close()
    conn.close()

# =============================================================
# 4️⃣ TEST: PUBLICAR HASH DE PRUEBA EN LA BLOCKCHAIN
# =============================================================
@bp_blockchain.route("/api/blockchain/test_tx", methods=["GET"])
def test_tx():
    """
    Envia un hash genérico de prueba a la Blockchain BFA para verificar
    la conexión, firma y publicación desde el backend Flask.
    """
    from app.utils.bfa_client import registrar_hash_en_bfa
    from app.utils.hashing import generar_hash

    # 🔹 Generar un hash ficticio
    mensaje = "Prueba de conexión Flask → Nodo BFA"
    hash_local = generar_hash(mensaje)

    try:
        tx_hash = registrar_hash_en_bfa(hash_local)
    except Exception as e:
        return jsonify({
            "estado": "error",
            "detalle": str(e)
        }), 500

    return jsonify({
        "estado": "ok",
        "mensaje": "✅ Transacción enviada correctamente a la Blockchain BFA",
        "hash_local": hash_local,
        "tx_hash": tx_hash
    }), 200
