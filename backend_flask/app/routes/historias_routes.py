# app/routes/historias_routes.py
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.database import db_cursor
from app.utils.permisos import requiere_rol
from app.utils.hashing import (
    PAYLOAD_VERSION_ACTUAL,
    campos_payload,
    filtra_activas,
    generar_hash_historia,
)

bp_historias = Blueprint("historias", __name__)


# =========================================================
#  Lectura canónica de evoluciones para el hash
# =========================================================
def leer_evoluciones(cursor, paciente_id, version=PAYLOAD_VERSION_ACTUAL):
    """Trae las evoluciones que entran al payload de la versión indicada.

    La query se arma desde la definición del payload (utils/hashing.py) y no a
    mano: si el SELECT y el payload se definen por separado, se van
    desincronizando y el hash deja de ser reproducible sin que nada avise.
    """
    columnas = ", ".join(campos_payload(version))
    where = "paciente_id = %s"
    if filtra_activas(version):
        # Las evoluciones dadas de baja no forman parte de la historia vigente.
        where += " AND activo = 1"

    cursor.execute(
        f"SELECT {columnas} FROM evoluciones WHERE {where} ORDER BY fecha ASC",
        (paciente_id,),
    )
    return cursor.fetchall()


# =========================================================
#  Función auxiliar: Actualizar historia consolidada
# =========================================================
def actualizar_historia(paciente_id, usuario_id, version=PAYLOAD_VERSION_ACTUAL):
    """Regenera la historia consolidada del paciente y su hash local.

    No toca `tx_hash`: el recibo de la TSA es la prueba de un sellado que
    efectivamente ocurrió, y borrarlo porque el contenido cambió destruiría esa
    evidencia. El histórico de sellados vive en `anclajes_historia`, y ahí cada
    anclaje conserva el hash con el que se sello.
    """
    with db_cursor() as (conn, cursor):
        evoluciones = leer_evoluciones(cursor, paciente_id, version)

        if not evoluciones:
            return None  # no hay evoluciones todavía

        hash_local, resumen_json = generar_hash_historia(evoluciones, version)

        cursor.execute("""
            INSERT INTO historias (paciente_id, usuario_id, resumen, hash_local, hash_version)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                usuario_id = VALUES(usuario_id),
                resumen = VALUES(resumen),
                hash_local = VALUES(hash_local),
                hash_version = VALUES(hash_version),
                fecha = NOW();
        """, (paciente_id, usuario_id, resumen_json, hash_local, version))

        conn.commit()

    return hash_local


# =========================================================
#  Crear nueva historia (manual o puntual)
# =========================================================
@bp_historias.route('/api/pacientes/<int:paciente_id>/historias', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
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
    with db_cursor() as (_conn, cursor):
        cursor.execute("""
            SELECT h.*, u.nombre AS nombre_usuario
            FROM historias h
            JOIN usuarios u ON h.usuario_id = u.id
            WHERE h.paciente_id = %s
            ORDER BY h.fecha DESC
        """, (paciente_id,))
        historias = cursor.fetchall()

    return jsonify(historias)