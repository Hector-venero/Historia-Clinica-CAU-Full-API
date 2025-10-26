# app/routes/blockchain_routes.py
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.utils.hashing import generar_hash
from app.utils.bfa_client import registrar_hash_en_bfa
from app.database import get_connection
from web3 import Web3
import hashlib
import json

bp_blockchain = Blueprint("blockchain", __name__)

# =============================================================
# 1️⃣ REGISTRAR HISTORIA EN LA BLOCKCHAIN BFA
# =============================================================
@bp_blockchain.route("/api/blockchain/registrar/<int:historia_id>", methods=["POST"])
@login_required
def registrar_en_bfa(historia_id):
    """
    Genera el hash de una historia clínica consolidada y lo publica en la Blockchain BFA.
    Guarda el hash y el tx_hash en la base de datos.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()
        # ✅ Si no encuentra historia por ID, intentar por paciente_id
    if not historia:
        cursor.execute("""
            SELECT * FROM historias
            WHERE paciente_id = %s
            ORDER BY fecha DESC
            LIMIT 1
        """, (historia_id,))
        historia = cursor.fetchone()

        if not historia:
            cursor.close()
            conn.close()
            return jsonify({"error": "Historia no encontrada"}), 404

        # corregimos el id real
        historia_id = historia["id"]

    if not historia:
        cursor.close()
        conn.close()
        return jsonify({"error": "Historia no encontrada"}), 404

    # 🔹 Usamos el resumen (JSON con todas las evoluciones)
    contenido = historia.get("resumen") or ""
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
        SET hash_local = %s, tx_hash = %s, fecha = NOW()
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
    web3 = Web3(Web3.HTTPProvider(BFA_URL))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()
    cursor.close()
    conn.close()

    if not historia:
        return jsonify({"error": "Historia no encontrada"}), 404

    if not historia.get("tx_hash"):
        return jsonify({"error": "La historia no tiene transacción registrada en BFA"}), 400

    # 🔹 Recalcular hash local desde resumen
    contenido = historia.get("resumen") or ""
    hash_local = generar_hash(contenido)

    # 🔹 Obtener hash publicado en BFA
    try:
        tx = web3.eth.get_transaction(historia["tx_hash"])
        input_data = tx["input"]
        # Convertimos a string hexadecimal limpio
        if isinstance(input_data, bytes):
            hash_bfa = input_data.hex()
        elif hasattr(input_data, "hex"):
            hash_bfa = input_data.hex()
        else:
            hash_bfa = str(input_data)

        # Limpiar prefijo '0x' si lo tiene
        if hash_bfa.startswith("0x"):
            hash_bfa = hash_bfa[2:]

    except Exception as e:
        return jsonify({"error": f"No se pudo obtener transacción: {str(e)}"}), 500

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
# 3️⃣ LISTAR AUDITORÍAS
# =============================================================
@bp_blockchain.route("/api/blockchain/auditorias", methods=["GET"])
@login_required
def listar_auditorias():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM auditorias_blockchain ORDER BY fecha DESC")
    registros = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(registros)

# =============================================================
# 🔧 GUARDAR AUDITORÍA (versión robusta con logs visibles)
# =============================================================
def _registrar_auditoria(historia_id, hash_local, hash_bfa, valido, usuario):
    
    print(f"🧾 Intentando registrar auditoría → historia_id={historia_id}, usuario={usuario}")

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 🧩 Verificar si el ID existe, o resolverlo como paciente_id
        cursor.execute("SELECT id FROM historias WHERE id = %s", (historia_id,))
        historia = cursor.fetchone()

        if not historia:
            # Intentamos interpretarlo como paciente_id
            cursor.execute("SELECT id FROM historias WHERE paciente_id = %s ORDER BY fecha DESC LIMIT 1", (historia_id,))
            historia = cursor.fetchone()

            if not historia:
                print(f"⚠️ No se encontró historia para id/paciente_id {historia_id}, no se guarda auditoría.")
                return

            historia_id = historia["id"]  # corregimos ID real

        sql = """
            INSERT INTO auditorias_blockchain (historia_id, hash_local, hash_bfa, valido, usuario)
            VALUES (%s, %s, %s, %s, %s)
        """
        # 🔧 Convertimos a string legible antes de guardar
        hash_bfa_str = (
            hash_bfa.hex() if hasattr(hash_bfa, "hex") else str(hash_bfa)
        )
        values = (historia_id, hash_local, hash_bfa_str, int(valido), usuario)

        print(f"🟢 INSERT auditorías: {values}")

        cursor.execute(sql, values)
        conn.commit()
        print(f"✅ Auditoría registrada correctamente para historia {historia_id}")

    except Exception as e:
        import traceback
        print("❌ Error al registrar auditoría:")
        traceback.print_exc()
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

# =============================================================
# 4️⃣ TEST: PUBLICAR HASH DE PRUEBA EN LA BLOCKCHAIN
# =============================================================
@bp_blockchain.route("/api/blockchain/test_tx", methods=["GET"])
def test_tx():
    from app.utils.bfa_client import registrar_hash_en_bfa
    from app.utils.hashing import generar_hash

    mensaje = "Prueba de conexión Flask → Nodo BFA"
    hash_local = generar_hash(mensaje)

    try:
        tx_hash = registrar_hash_en_bfa(hash_local)
    except Exception as e:
        return jsonify({"estado": "error", "detalle": str(e)}), 500

    return jsonify({
        "estado": "ok",
        "mensaje": "✅ Transacción enviada correctamente a la Blockchain BFA",
        "hash_local": hash_local,
        "tx_hash": tx_hash
    }), 200

# =============================================================
# 5️⃣ VERIFICAR INTEGRIDAD DE HISTORIA CLÍNICA CONSOLIDADA
# =============================================================
@bp_blockchain.route('/api/blockchain/verificar/historia/<int:paciente_id>', methods=['GET'])
@login_required
def verificar_historia_blockchain(paciente_id):
    """
    Compara el hash local de la historia clínica consolidada
    con el registrado en la Blockchain Federal Argentina.
    Registra una auditoría.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, hash_local, tx_hash, fecha
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

    if not historia.get("tx_hash"):
        return jsonify({"error": "La historia no tiene transacción registrada en BFA"}), 400

    from app.utils.bfa_client import BFA_URL
    web3 = Web3(Web3.HTTPProvider(BFA_URL))

    try:
        tx = web3.eth.get_transaction(historia["tx_hash"])
        input_data = tx["input"]
        if isinstance(input_data, bytes):
            input_data = input_data.hex()
        elif hasattr(input_data, "hex"):
            input_data = input_data.hex()
        hash_bfa = str(input_data)[2:] if input_data.startswith("0x") else str(input_data)
    except Exception as e:
        return jsonify({"error": f"No se pudo obtener transacción: {str(e)}"}), 500

    valido = (historia["hash_local"] == hash_bfa)
    _registrar_auditoria(historia["id"], historia["hash_local"], hash_bfa, valido, current_user.username)

    return jsonify({
        "paciente_id": paciente_id,
        "hash_local": historia["hash_local"],
        "hash_bfa": hash_bfa,
        "tx_hash": historia["tx_hash"],
        "valido": valido,
        "mensaje": "✅ Integridad verificada" if valido else "❌ La historia fue modificada",
        "fecha": str(historia["fecha"])
    })

# =============================================================
# 6️⃣ VERIFICAR INTEGRIDAD DE UNA EVOLUCIÓN INDIVIDUAL
# =============================================================
@bp_blockchain.route('/api/blockchain/verificar/evolucion/<int:evolucion_id>', methods=['GET'])
@login_required
def verificar_evolucion_blockchain(evolucion_id):
    """
    Verifica la integridad de una evolución individual comparando
    su hash local con el registrado en la BFA (modo simulado o real).
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM evoluciones WHERE id = %s", (evolucion_id,))
    evolucion = cursor.fetchone()
    cursor.close()
    conn.close()

    if not evolucion:
        return jsonify({"error": "Evolución no encontrada"}), 404

    data = {
        "id": evolucion["id"],
        "paciente_id": evolucion["paciente_id"],
        "fecha": str(evolucion["fecha"]),
        "contenido": evolucion["contenido"],
        "usuario_id": evolucion["usuario_id"],
    }
    resumen_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
    hash_local = hashlib.sha256(resumen_json.encode()).hexdigest()

    try:
        from app.utils.bfa_client import verificar_hash_en_bfa
        hash_bfa = verificar_hash_en_bfa(hash_local)
    except Exception as e:
        return jsonify({"error": f"No se pudo verificar en BFA: {str(e)}"}), 500

    valido = (hash_local == hash_bfa)

    return jsonify({
        "evolucion_id": evolucion_id,
        "hash_local": hash_local,
        "hash_bfa": hash_bfa,
        "valido": valido,
        "mensaje": "✅ Integridad verificada" if valido else "❌ Evolución modificada"
    })


@bp_blockchain.route("/api/blockchain/auditorias/<int:paciente_id>", methods=["GET"])
@login_required
def listar_auditorias_paciente(paciente_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.*, h.paciente_id
        FROM auditorias_blockchain a
        JOIN historias h ON a.historia_id = h.id
        WHERE h.paciente_id = %s
        ORDER BY a.fecha DESC
    """, (paciente_id,))
    registros = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(registros)
