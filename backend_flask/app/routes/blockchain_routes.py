# app/routes/blockchain_routes.py
"""Anclaje y verificacion de historias clinicas en BFA (via la API TSA).

Dos decisiones centrales:

1. La verificacion distingue tres estados. La TSA agrupa hashes en lotes y los
   ancla cada varios minutos: entre el sellado y su confirmacion responde
   `pending`, que no significa adulteracion. Tratar `pending` (o un timeout de
   red) como "invalido" mostraba "la historia fue modificada" sobre una
   historia intacta, y ademas dejaba esa conclusion escrita en la tabla de
   auditoria. Solo se audita cuando hay un veredicto real.

2. Cada sellado se registra en `anclajes_blockchain`, que es append-only. La
   historia consolidada se recalcula cada vez que se carga una evolucion, asi
   que su `hash_local` cambia; si el recibo viviera solo en `historias`,
   quedaria apuntando a un hash inexistente y se perderia la prueba. Verificar
   usa el hash y el recibo del anclaje, no el estado actual de la historia.
"""

from flask import Blueprint, current_app, jsonify
from flask_login import current_user, login_required
import requests

from app.database import db_cursor
from app.utils.bfa_client import (
    ESTADO_OK,
    ESTADO_PENDIENTE,
    get_bfa_status,
    parse_permanent_rd,
    registrar_hash_en_bfa,
    verificar_hash_en_bfa,
)
from app.utils.hashing import PAYLOAD_VERSION_ACTUAL, generar_hash, generar_hash_evolucion
from app.utils.permisos import requiere_rol, requiere_modulo

bp_blockchain = Blueprint("blockchain", __name__)


# =============================================================
#  Helpers
# =============================================================
def _verificar_en_tsa(hash_local, rd):
    """Consulta la TSA y traduce su respuesta.

    Devuelve (resultado, error_de_red). Exactamente uno de los dos es None:
    un problema de conectividad no es un veredicto sobre la integridad y no
    debe registrarse como tal.
    """
    try:
        data = verificar_hash_en_bfa(hash_local, rd)
    except requests.RequestException as exc:
        return None, str(exc)

    estado = data.get("status")
    decoded = parse_permanent_rd(data.get("permanent_rd", ""))

    if estado == ESTADO_OK:
        return {
            "estado": "confirmado",
            "valido": True,
            "block_number": decoded.get("block_number"),
            "attestation_time": data.get("attestation_time"),
            "permanent_rd": data.get("permanent_rd"),
            "attestation": data,
            "mensaje": "✅ Integridad verificada en blockchain",
        }, None

    if estado == ESTADO_PENDIENTE:
        return {
            "estado": "pendiente",
            "valido": None,
            "block_number": None,
            "attestation_time": None,
            "permanent_rd": None,
            "attestation": data,
            "mensaje": "⏳ Sellado registrado, esperando confirmación en blockchain",
        }, None

    return {
        "estado": "error",
        "valido": False,
        "block_number": None,
        "attestation_time": None,
        "permanent_rd": None,
        "attestation": data,
        "mensaje": "❌ El contenido no coincide con lo sellado en blockchain",
    }, None


def _registrar_auditoria(cursor, historia_id, hash_local, hash_bfa, valido, usuario):
    """Deja constancia de una verificacion con veredicto.

    No se llama para `pendiente` ni ante errores de red: la auditoria registra
    conclusiones, no intentos.
    """
    cursor.execute(
        """
        INSERT INTO auditorias_blockchain (historia_id, hash_local, hash_bfa, valido, usuario)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (historia_id, hash_local, str(hash_bfa) if hash_bfa else None, int(valido), usuario),
    )


def _actualizar_anclaje(cursor, anclaje_id, resultado):
    cursor.execute(
        """
        UPDATE anclajes_blockchain
        SET estado = %s,
            permanent_rd = COALESCE(%s, permanent_rd),
            block_number = COALESCE(%s, block_number),
            attestation_time = COALESCE(%s, attestation_time),
            verificado_en = NOW()
        WHERE id = %s
        """,
        (
            resultado["estado"],
            resultado.get("permanent_rd"),
            resultado.get("block_number"),
            resultado.get("attestation_time"),
            anclaje_id,
        ),
    )


def _ultimo_anclaje(cursor, paciente_id):
    """Ultimo sellado de la historia consolidada de un paciente."""
    cursor.execute(
        """
        SELECT id, historia_id, hash_local, hash_version, recibo_tsa, estado
        FROM anclajes_blockchain
        WHERE paciente_id = %s AND entidad_tipo = 'historia'
        ORDER BY creado_en DESC, id DESC
        LIMIT 1
        """,
        (paciente_id,),
    )
    return cursor.fetchone()


def _ultimo_anclaje_evolucion(cursor, evolucion_id):
    """Ultimo sellado de una evolucion puntual.

    Es un anclaje propio, no el de la historia: mezclarlos fue el bug de la
    implementacion anterior.
    """
    cursor.execute(
        """
        SELECT id, evolucion_id, hash_local, hash_version, recibo_tsa, estado
        FROM anclajes_blockchain
        WHERE evolucion_id = %s AND entidad_tipo = 'evolucion'
        ORDER BY creado_en DESC, id DESC
        LIMIT 1
        """,
        (evolucion_id,),
    )
    return cursor.fetchone()


def _historia_por_id_o_paciente(cursor, identificador):
    """La ruta historica acepta tanto un historia_id como un paciente_id."""
    cursor.execute("SELECT * FROM historias WHERE id = %s", (identificador,))
    historia = cursor.fetchone()
    if historia:
        return historia
    cursor.execute(
        "SELECT * FROM historias WHERE paciente_id = %s ORDER BY fecha DESC LIMIT 1",
        (identificador,),
    )
    return cursor.fetchone()


# =============================================================
# 1) SELLAR UNA HISTORIA EN BFA
# =============================================================
@bp_blockchain.route("/api/blockchain/registrar/<int:historia_id>", methods=["POST"])
@login_required
@requiere_modulo('blockchain')
@requiere_rol("director", "profesional")
def registrar_en_bfa(historia_id):
    """Sella el hash de una historia consolidada y registra el anclaje."""
    with db_cursor() as (conn, cursor):
        historia = _historia_por_id_o_paciente(cursor, historia_id)
        if not historia:
            return jsonify({"error": "Historia no encontrada"}), 404

        hash_local = historia.get("hash_local")
        if not hash_local:
            return jsonify({
                "error": "La historia no tiene hash_local calculado. "
                         "Actualizá la historia consolidada primero."
            }), 400

        hash_version = historia.get("hash_version") or PAYLOAD_VERSION_ACTUAL

        try:
            rd = registrar_hash_en_bfa(hash_local)
        except Exception as exc:
            current_app.logger.exception("Fallo el sellado en la TSA")
            return jsonify({"error": f"No se pudo sellar en la BFA: {exc}"}), 502

        # Append-only: cada sellado es una fila nueva, nunca pisa a la anterior.
        cursor.execute(
            """
            INSERT INTO anclajes_blockchain
                (paciente_id, historia_id, entidad_tipo, hash_local, hash_version, recibo_tsa, estado, usuario)
            VALUES (%s, %s, 'historia', %s, %s, %s, 'pendiente', %s)
            """,
            (
                historia["paciente_id"],
                historia["id"],
                hash_local,
                hash_version,
                rd,
                current_user.username,
            ),
        )

        # `historias.tx_hash` queda como puntero al ultimo recibo, por
        # comodidad de lectura. La fuente de verdad es anclajes_blockchain.
        cursor.execute(
            "UPDATE historias SET tx_hash = %s, fecha_anclaje_bfa = NOW(), estado_bfa = 'pendiente' WHERE id = %s",
            (rd, historia["id"]),
        )
        conn.commit()

    return jsonify({
        "historia_id": historia["id"],
        "paciente_id": historia["paciente_id"],
        "hash": hash_local,
        "hash_version": hash_version,
        "recibo_tsa": rd,
        "tx_hash": rd,  # alias por compat
        "estado": "pendiente",
        "mensaje": "✅ Hash sellado en BFA. La confirmación en blockchain puede demorar unos minutos.",
    }), 201


# =============================================================
# 2) VERIFICAR UNA HISTORIA (por historia_id)
# =============================================================
@bp_blockchain.route("/api/blockchain/verificar/<int:historia_id>", methods=["GET"])
@login_required
@requiere_modulo('blockchain')
def verificar_historia(historia_id):
    with db_cursor() as (conn, cursor):
        historia = _historia_por_id_o_paciente(cursor, historia_id)
        if not historia:
            return jsonify({"error": "Historia no encontrada"}), 404

        respuesta, codigo = _verificar_paciente(conn, cursor, historia["paciente_id"])

    return jsonify(respuesta), codigo


# =============================================================
# 3) VERIFICAR LA HISTORIA CONSOLIDADA DE UN PACIENTE
# =============================================================
@bp_blockchain.route("/api/blockchain/verificar/historia/<int:paciente_id>", methods=["GET"])
@login_required
@requiere_modulo('blockchain')
def verificar_historia_blockchain(paciente_id):
    with db_cursor() as (conn, cursor):
        respuesta, codigo = _verificar_paciente(conn, cursor, paciente_id)
    return jsonify(respuesta), codigo


def _verificar_paciente(conn, cursor, paciente_id):
    """Verifica el ultimo anclaje del paciente. Devuelve (payload, http_status)."""
    anclaje = _ultimo_anclaje(cursor, paciente_id)
    if not anclaje:
        return {"error": "La historia no tiene sellado registrado en BFA"}, 400

    resultado, error_red = _verificar_en_tsa(anclaje["hash_local"], anclaje["recibo_tsa"])

    if error_red is not None:
        # No se pudo consultar la TSA. No se audita ni se concluye nada.
        return {
            "paciente_id": paciente_id,
            "estado": "indeterminado",
            "valido": None,
            "mensaje": "⚠️ No se pudo contactar a la TSA de BFA. Reintentá en unos minutos.",
            "detalle": error_red,
        }, 503

    _actualizar_anclaje(cursor, anclaje["id"], resultado)

    # Solo se audita cuando hay veredicto: 'pendiente' no lo es.
    if resultado["valido"] is not None:
        _registrar_auditoria(
            cursor,
            anclaje["historia_id"],
            anclaje["hash_local"],
            anclaje["recibo_tsa"],
            resultado["valido"],
            current_user.username,
        )

    cursor.execute(
        "UPDATE historias SET estado_bfa = %s WHERE id = %s",
        (resultado["estado"], anclaje["historia_id"]),
    )
    conn.commit()

    return {
        "paciente_id": paciente_id,
        "historia_id": anclaje["historia_id"],
        "hash_local": anclaje["hash_local"],
        "hash_version": anclaje["hash_version"],
        "recibo_tsa": anclaje["recibo_tsa"],
        "tx_hash": anclaje["recibo_tsa"],  # alias por compat
        "estado": resultado["estado"],
        "valido": resultado["valido"],
        "bloque": resultado["block_number"],
        "attestation_time": resultado["attestation_time"],
        "permanent_rd": resultado["permanent_rd"],
        "attestation": resultado["attestation"],
        "mensaje": resultado["mensaje"],
    }, 200


# =============================================================
# 4) HISTORIAL DE ANCLAJES DE UN PACIENTE
# =============================================================
@bp_blockchain.route("/api/blockchain/anclajes/<int:paciente_id>", methods=["GET"])
@login_required
@requiere_modulo('blockchain')
def listar_anclajes(paciente_id):
    """Todos los sellados del paciente, del mas reciente al mas viejo.

    Cada fila es una prueba independiente: que en tal momento el contenido
    resumido por ese hash existia y se anclo.
    """
    with db_cursor() as (_conn, cursor):
        cursor.execute(
            """
            SELECT id, historia_id, hash_local, hash_version, recibo_tsa, permanent_rd,
                   estado, block_number, attestation_time, usuario, creado_en, verificado_en
            FROM anclajes_blockchain
            WHERE paciente_id = %s
            ORDER BY creado_en DESC, id DESC
            """,
            (paciente_id,),
        )
        anclajes = cursor.fetchall()
    return jsonify(anclajes)


# =============================================================
# 5) ANCLAJE Y VERIFICACIÓN DE EVOLUCIONES INDIVIDUALES
# =============================================================
@bp_blockchain.route("/api/blockchain/registrar/evolucion/<int:evolucion_id>", methods=["POST"])
@login_required
@requiere_modulo('blockchain')
@requiere_rol("director", "profesional")
def registrar_evolucion_en_bfa(evolucion_id):
    """Sella una evolucion puntual, con su propio hash y su propio recibo.

    Sirve para probar la integridad de un acto medico concreto sin depender de
    la historia consolidada, que cambia cada vez que se carga una evolucion
    nueva y por lo tanto necesita reanclarse.
    """
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT * FROM evoluciones WHERE id = %s", (evolucion_id,))
        evolucion = cursor.fetchone()
        if not evolucion:
            return jsonify({"error": "Evolución no encontrada"}), 404

        hash_local, _payload = generar_hash_evolucion(evolucion, PAYLOAD_VERSION_ACTUAL)

        try:
            rd = registrar_hash_en_bfa(hash_local)
        except Exception as exc:
            current_app.logger.exception("Fallo el sellado de la evolución en la TSA")
            return jsonify({"error": f"No se pudo sellar en la BFA: {exc}"}), 502

        cursor.execute(
            """
            INSERT INTO anclajes_blockchain
                (paciente_id, evolucion_id, entidad_tipo, hash_local, hash_version,
                 recibo_tsa, estado, usuario)
            VALUES (%s, %s, 'evolucion', %s, %s, %s, 'pendiente', %s)
            """,
            (
                evolucion["paciente_id"],
                evolucion_id,
                hash_local,
                PAYLOAD_VERSION_ACTUAL,
                rd,
                current_user.username,
            ),
        )

        # Punteros de conveniencia en la propia evolución; la fuente de verdad
        # sigue siendo anclajes_blockchain.
        cursor.execute(
            """
            UPDATE evoluciones
            SET hash_local = %s, tx_hash = %s, fecha_anclaje_bfa = NOW(), estado_bfa = 'pendiente'
            WHERE id = %s
            """,
            (hash_local, rd, evolucion_id),
        )
        conn.commit()

    return jsonify({
        "evolucion_id": evolucion_id,
        "paciente_id": evolucion["paciente_id"],
        "hash": hash_local,
        "hash_version": PAYLOAD_VERSION_ACTUAL,
        "recibo_tsa": rd,
        "estado": "pendiente",
        "mensaje": "✅ Evolución sellada en BFA. La confirmación puede demorar unos minutos.",
    }), 201


@bp_blockchain.route("/api/blockchain/verificar/evolucion/<int:evolucion_id>", methods=["GET"])
@login_required
@requiere_modulo('blockchain')
def verificar_evolucion_blockchain(evolucion_id):
    """Verifica una evolucion contra SU PROPIO recibo.

    La implementacion anterior calculaba el hash de la evolucion y lo verificaba
    contra el recibo de la historia consolidada. Son dos hashes distintos, asi
    que la TSA respondia failure siempre: mostraba "evolucion modificada" sobre
    evoluciones intactas.
    """
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id FROM evoluciones WHERE id = %s", (evolucion_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Evolución no encontrada"}), 404

        anclaje = _ultimo_anclaje_evolucion(cursor, evolucion_id)
        if not anclaje:
            return jsonify({
                "evolucion_id": evolucion_id,
                "estado": "sin_anclaje",
                "valido": None,
                "error": "Esta evolución todavía no fue sellada en BFA",
            }), 400

        resultado, error_red = _verificar_en_tsa(anclaje["hash_local"], anclaje["recibo_tsa"])

        if error_red is not None:
            return jsonify({
                "evolucion_id": evolucion_id,
                "estado": "indeterminado",
                "valido": None,
                "mensaje": "⚠️ No se pudo contactar a la TSA de BFA. Reintentá en unos minutos.",
                "detalle": error_red,
            }), 503

        _actualizar_anclaje(cursor, anclaje["id"], resultado)

        # Solo se audita cuando hay veredicto: 'pendiente' no lo es.
        if resultado["valido"] is not None:
            _registrar_auditoria(
                cursor,
                None,
                anclaje["hash_local"],
                anclaje["recibo_tsa"],
                resultado["valido"],
                current_user.username,
            )

        cursor.execute(
            "UPDATE evoluciones SET estado_bfa = %s WHERE id = %s",
            (resultado["estado"], evolucion_id),
        )
        conn.commit()

    return jsonify({
        "evolucion_id": evolucion_id,
        "hash_local": anclaje["hash_local"],
        "hash_version": anclaje["hash_version"],
        "recibo_tsa": anclaje["recibo_tsa"],
        "estado": resultado["estado"],
        "valido": resultado["valido"],
        "bloque": resultado["block_number"],
        "attestation_time": resultado["attestation_time"],
        "permanent_rd": resultado["permanent_rd"],
        "mensaje": resultado["mensaje"],
    }), 200


# =============================================================
# 6) AUDITORÍAS
# =============================================================
@bp_blockchain.route("/api/blockchain/auditorias", methods=["GET"])
@login_required
@requiere_modulo('blockchain')
@requiere_rol("director")
def listar_auditorias():
    with db_cursor() as (_conn, cursor):
        cursor.execute("SELECT * FROM auditorias_blockchain ORDER BY fecha DESC")
        registros = cursor.fetchall()
    return jsonify(registros)


@bp_blockchain.route("/api/blockchain/auditorias/<int:paciente_id>", methods=["GET"])
@login_required
@requiere_modulo('blockchain')
def listar_auditorias_paciente(paciente_id):
    with db_cursor() as (_conn, cursor):
        cursor.execute(
            """
            SELECT a.*, h.paciente_id
            FROM auditorias_blockchain a
            JOIN historias h ON a.historia_id = h.id
            WHERE h.paciente_id = %s
            ORDER BY a.fecha DESC
            """,
            (paciente_id,),
        )
        registros = cursor.fetchall()
    return jsonify(registros)


# =============================================================
# 7) DIAGNÓSTICO
# =============================================================
@bp_blockchain.route("/api/blockchain/estado", methods=["GET"])
@login_required
@requiere_modulo('blockchain')
@requiere_rol("director")
def estado_bfa():
    """Disponibilidad de la TSA."""
    return jsonify(get_bfa_status())


@bp_blockchain.route("/api/blockchain/test_tx", methods=["GET"])
@login_required
@requiere_modulo('blockchain')
@requiere_rol("director")
def test_tx():
    """Sella un hash de prueba. Consume cuota real de la TSA.

    Antes no pedia autenticacion: cualquiera podia sellar contra la identidad
    BFA de la institucion. Ahora requiere rol director y esta apagado en
    produccion salvo que se habilite explicitamente.
    """
    if not current_app.config.get("ENABLE_BLOCKCHAIN_TEST_ENDPOINTS", False):
        return jsonify({
            "error": "Endpoint de prueba deshabilitado. "
                     "Habilitalo con ENABLE_BLOCKCHAIN_TEST_ENDPOINTS=true."
        }), 403

    hash_local = generar_hash("Prueba de conexión Flask → BFA (TSA)")
    try:
        rd = registrar_hash_en_bfa(hash_local)
    except Exception as exc:
        current_app.logger.exception("Fallo el test de sellado")
        return jsonify({"estado": "error", "detalle": str(exc)}), 502

    return jsonify({
        "estado": "ok",
        "mensaje": "✅ Hash de prueba sellado en BFA (TSA)",
        "hash_local": hash_local,
        "recibo_tsa": rd,
        "tx_hash": rd,
    }), 200
