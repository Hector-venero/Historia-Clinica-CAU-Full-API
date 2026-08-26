# app/routes/ausencias_routes.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.fechas import a_iso_arg
from app.utils.permisos import requiere_rol
from datetime import datetime

bp_ausencias = Blueprint("ausencias", __name__)

# ============================================================
#  Crear una ausencia (bloqueo de agenda)
# ============================================================
@bp_ausencias.route("/api/ausencias", methods=["POST"])
@login_required
@requiere_rol("director", "profesional", "administrativo", "area")
def crear_ausencia():
    data = request.get_json(silent=True) or {}
    
    # Si es profesional/area, forzamos su ID. Si es director, puede elegir.
    if current_user.rol in ["profesional", "area"]:
        usuario_id = current_user.id
    else:
        usuario_id = data.get("usuario_id") or current_user.id

    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    motivo = data.get("motivo", "")

    if not fecha_inicio or not fecha_fin:
        return jsonify({"error": "Se requieren fecha_inicio y fecha_fin"}), 400

    # Restricción extra de seguridad
    if current_user.rol in ["profesional", "area"] and usuario_id != current_user.id:
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


# ============================================================
#  Listar ausencias
# ============================================================
@bp_ausencias.route("/api/ausencias", methods=["GET"])
@login_required
@requiere_rol("director", "profesional", "administrativo", "area")
def listar_ausencias():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 👇 CAMBIO: "area" solo ve lo suyo, igual que profesional
    if current_user.rol in ["profesional", "area"]:
        cursor.execute("""
            SELECT a.*, u.nombre AS nombre_usuario
            FROM ausencias a
            JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.usuario_id = %s
            ORDER BY fecha_inicio
        """, (current_user.id,))
    else:
        # Director / Admin ven todo
        cursor.execute("""
            SELECT a.*, u.nombre AS nombre_usuario
            FROM ausencias a
            JOIN usuarios u ON a.usuario_id = u.id
            ORDER BY fecha_inicio
        """)
    
    ausencias = cursor.fetchall()
    cursor.close()
    conn.close()

    # jsonify serializa los DATETIME al formato de fecha HTTP y los etiqueta
    # "GMT", aunque estan guardados en hora argentina:
    #
    #     "fecha_inicio": "Thu, 10 Sep 2026 08:00:00 GMT"   <- son las 08:00 ART
    #
    # Quien los lea como UTC corre el valor tres horas. En el navegador eso hacia
    # que una ausencia de dia completo (00:00 a 23:59) se leyera como 21:00 del
    # dia anterior a 20:59, con lo que dejaba de reconocerse como dia completo y
    # el dia no se bloqueaba en el calendario de Nuevo Turno.
    for ausencia in ausencias:
        ausencia["fecha_inicio"] = a_iso_arg(ausencia.get("fecha_inicio"))
        ausencia["fecha_fin"] = a_iso_arg(ausencia.get("fecha_fin"))

    return jsonify(ausencias)


# ============================================================
#  Eliminar una ausencia
# ============================================================
@bp_ausencias.route("/api/ausencias/<int:ausencia_id>", methods=["DELETE"])
@login_required
@requiere_rol("director", "profesional", "administrativo", "area")
def eliminar_ausencia(ausencia_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM ausencias WHERE id=%s", (ausencia_id,))
    ausencia = cursor.fetchone()
    if not ausencia:
        cursor.close(); conn.close()
        return jsonify({"error": "Ausencia no encontrada"}), 404

    # Restricción: un médico/area solo puede eliminar sus propias ausencias
    # 👇 CAMBIO: Agregamos "area" a la restricción
    if current_user.rol in ["profesional", "area"] and ausencia["usuario_id"] != current_user.id:
        cursor.close(); conn.close()
        return jsonify({"error": "No autorizado"}), 403

    cursor.execute("DELETE FROM ausencias WHERE id=%s", (ausencia_id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Ausencia eliminada ✅"})