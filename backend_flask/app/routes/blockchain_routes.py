# app/routes/blockchain_routes.py
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.utils.bfa_client import registrar_hash_en_bfa, verificar_hash_en_bfa, parse_permanent_rd
from app.database import get_connection
import hashlib
import json

bp_blockchain = Blueprint("blockchain", __name__)

# =============================================================
# 1️⃣ REGISTRAR HISTORIA EN LA BLOCKCHAIN BFA (vía TSA)
# =============================================================
@bp_blockchain.route("/api/blockchain/registrar/<int:historia_id>", methods=["POST"])
@login_required
def registrar_en_bfa(historia_id):
    """
    Genera el hash de una historia clínica consolidada y lo sella en BFA vía la TSA oficial.
    Guarda el hash y el recibo (rd) en la base de datos en la columna `tx_hash`.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()

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

        historia_id = historia["id"]

    hash_local = historia.get("hash_local")
    if not hash_local:
        cursor.close()
        conn.close()
        return jsonify({"error": "La historia no tiene hash_local calculado. Actualizá la historia consolidada primero."}), 400

    try:
        rd = registrar_hash_en_bfa(hash_local)
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({"error": f"No se pudo sellar en la BFA: {str(e)}"}), 500

    cursor.execute("""
        UPDATE historias
        SET hash_local = %s, tx_hash = %s, fecha = NOW()
        WHERE id = %s
    """, (hash_local, rd, historia_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "historia_id": historia_id,
        "hash": hash_local,
        "recibo_tsa": rd,
        "tx_hash": rd,  # alias por compat
        "mensaje": "✅ Hash sellado correctamente en la Blockchain BFA (TSA). La confirmación en blockchain puede demorar unos segundos."
    }), 201


# =============================================================
# 2️⃣ VERIFICAR INTEGRIDAD DE UNA HISTORIA (vía TSA)
# =============================================================
@bp_blockchain.route("/api/blockchain/verificar/<int:historia_id>", methods=["GET"])
@login_required
def verificar_historia(historia_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()
    cursor.close()
    conn.close()

    if not historia:
        return jsonify({"error": "Historia no encontrada"}), 404

    if not historia.get("tx_hash"):
        return jsonify({"error": "La historia no tiene sellado registrado en BFA"}), 400

    hash_local = historia.get("hash_local") or ""
    rd = historia["tx_hash"]

    try:
        attestation = verificar_hash_en_bfa(hash_local, rd)
        valido = True
    except Exception as e:
        attestation = {"messages": str(e)}
        valido = False

    _registrar_auditoria(historia_id, hash_local, rd, valido, current_user.username)

    decoded = parse_permanent_rd(attestation.get("permanent_rd", "")) if valido else {}

    return jsonify({
        "historia_id": historia_id,
        "hash_local": hash_local,
        "recibo_tsa": rd,
        "tx_hash": rd,  # alias por compat
        "valido": valido,
        "bloque": decoded.get("block_number"),
        "attestation_time": attestation.get("attestation_time"),
        "permanent_rd": attestation.get("permanent_rd"),
        "attestation": attestation,
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
# 🔧 GUARDAR AUDITORÍA
# =============================================================
def _registrar_auditoria(historia_id, hash_local, hash_bfa, valido, usuario):
    print(f"🧾 Intentando registrar auditoría → historia_id={historia_id}, usuario={usuario}")

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM historias WHERE id = %s", (historia_id,))
        historia = cursor.fetchone()

        if not historia:
            cursor.execute("SELECT id FROM historias WHERE paciente_id = %s ORDER BY fecha DESC LIMIT 1", (historia_id,))
            historia = cursor.fetchone()

            if not historia:
                print(f"⚠️ No se encontró historia para id/paciente_id {historia_id}, no se guarda auditoría.")
                return

            historia_id = historia["id"]

        sql = """
            INSERT INTO auditorias_blockchain (historia_id, hash_local, hash_bfa, valido, usuario)
            VALUES (%s, %s, %s, %s, %s)
        """
        hash_bfa_str = str(hash_bfa) if hash_bfa is not None else None
        values = (historia_id, hash_local, hash_bfa_str, int(valido), usuario)

        cursor.execute(sql, values)
        conn.commit()
        print(f"✅ Auditoría registrada correctamente para historia {historia_id}")

    except Exception:
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
# 4️⃣ TEST: SELLAR HASH DE PRUEBA EN LA BLOCKCHAIN
# =============================================================
@bp_blockchain.route("/api/blockchain/test_tx", methods=["GET"])
def test_tx():
    mensaje = "Prueba de conexión Flask → BFA (TSA)"
    hash_local = hashlib.sha256(mensaje.encode("utf-8")).hexdigest()

    try:
        rd = registrar_hash_en_bfa(hash_local)
    except Exception as e:
        return jsonify({"estado": "error", "detalle": str(e)}), 500

    return jsonify({
        "estado": "ok",
        "mensaje": "✅ Hash sellado correctamente en la Blockchain BFA (TSA)",
        "hash_local": hash_local,
        "tx_hash": rd
    }), 200


# =============================================================
# 5️⃣ VERIFICAR INTEGRIDAD DE HISTORIA CLÍNICA CONSOLIDADA POR PACIENTE
# =============================================================
@bp_blockchain.route('/api/blockchain/verificar/historia/<int:paciente_id>', methods=['GET'])
@login_required
def verificar_historia_blockchain(paciente_id):
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
        return jsonify({"error": "La historia no tiene sellado registrado en BFA"}), 400

    try:
        attestation = verificar_hash_en_bfa(historia["hash_local"], historia["tx_hash"])
        valido = True
    except Exception as e:
        attestation = {"messages": str(e)}
        valido = False

    _registrar_auditoria(historia["id"], historia["hash_local"], historia["tx_hash"], valido, current_user.username)

    decoded = parse_permanent_rd(attestation.get("permanent_rd", "")) if valido else {}

    return jsonify({
        "paciente_id": paciente_id,
        "hash_local": historia["hash_local"],
        "recibo_tsa": historia["tx_hash"],
        "tx_hash": historia["tx_hash"],  # alias por compat
        "valido": valido,
        "bloque": decoded.get("block_number"),
        "attestation_time": attestation.get("attestation_time"),
        "permanent_rd": attestation.get("permanent_rd"),
        "attestation": attestation,
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
    Verifica la integridad de una evolución individual contra la TSA.
    Requiere que la evolución (o su historia) tenga un `tx_hash` (rd) almacenado.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM evoluciones WHERE id = %s", (evolucion_id,))
    evolucion = cursor.fetchone()

    if not evolucion:
        cursor.close()
        conn.close()
        return jsonify({"error": "Evolución no encontrada"}), 404

    cursor.execute("""
        SELECT tx_hash FROM historias
        WHERE paciente_id = %s AND tx_hash IS NOT NULL
        ORDER BY fecha DESC LIMIT 1
    """, (evolucion["paciente_id"],))
    historia = cursor.fetchone()
    cursor.close()
    conn.close()

    data = {
        "id": evolucion["id"],
        "paciente_id": evolucion["paciente_id"],
        "fecha": str(evolucion["fecha"]),
        "contenido": evolucion["contenido"],
        "usuario_id": evolucion["usuario_id"],
    }
    resumen_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
    hash_local = hashlib.sha256(resumen_json.encode()).hexdigest()

    if not historia or not historia.get("tx_hash"):
        return jsonify({
            "evolucion_id": evolucion_id,
            "hash_local": hash_local,
            "valido": False,
            "mensaje": "❌ La historia del paciente no tiene sellado en BFA"
        }), 400

    rd = historia["tx_hash"]
    try:
        attestation = verificar_hash_en_bfa(hash_local, rd)
        valido = True
    except Exception as e:
        attestation = {"messages": str(e)}
        valido = False

    decoded = parse_permanent_rd(attestation.get("permanent_rd", "")) if valido else {}

    return jsonify({
        "evolucion_id": evolucion_id,
        "hash_local": hash_local,
        "recibo_tsa": rd,
        "tx_hash": rd,  # alias por compat
        "valido": valido,
        "bloque": decoded.get("block_number"),
        "attestation_time": attestation.get("attestation_time"),
        "permanent_rd": attestation.get("permanent_rd"),
        "attestation": attestation,
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
