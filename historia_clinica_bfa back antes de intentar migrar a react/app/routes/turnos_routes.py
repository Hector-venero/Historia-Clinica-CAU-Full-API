from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.database import get_connection
from app.utils.permisos import requiere_rol
from app import mail
from flask_mail import Message

bp_turnos = Blueprint("turnos", __name__)

@bp_turnos.route('/api/turnos', methods=['GET', 'POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def api_turnos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        if current_user.rol == 'profesional':
            # Solo ve sus propios turnos
            cursor.execute("""
                SELECT t.id, t.fecha, t.motivo, p.nombre, p.dni, u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON t.paciente_id = p.id
                JOIN usuarios u ON t.usuario_id = u.id
                WHERE t.usuario_id = %s
                ORDER BY t.fecha ASC
            """, (current_user.id,))
        else:
            # Administrativos o director → ven todos los turnos
            cursor.execute("""
                SELECT t.id, t.fecha, t.motivo, p.nombre, p.dni, u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON t.paciente_id = p.id
                JOIN usuarios u ON t.usuario_id = u.id
                ORDER BY t.fecha ASC
            """)

        turnos = cursor.fetchall()
        cursor.close()
        conn.close()

        eventos = [{
            "id": t["id"],
            "paciente": t["nombre"],
            "dni": t["dni"],
            "start": t["fecha"].isoformat(),
            "description": t["motivo"],
            "profesional": t["profesional"]
        } for t in turnos]

        return jsonify(eventos)
        

    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"error": "Faltan datos"}), 400

        paciente_id = data.get("paciente_id")
        usuario_id = data.get("usuario_id")
        fecha = data.get("fecha")
        motivo = data.get("motivo")

        if not (paciente_id and usuario_id and fecha):
            return jsonify({"error": "Campos obligatorios faltantes"}), 400

        # 🔒 Restricción: un profesional solo puede asignarse turnos a sí mismo
        if current_user.rol == 'profesional' and usuario_id != current_user.id:
            return jsonify({"error": "No puede asignar turnos a otros profesionales"}), 403
        
        try:
            # ✅ Validar que el profesional no tenga una ausencia en esa fecha
            cursor.execute("""
                SELECT 1
                FROM ausencias
                WHERE usuario_id = %s
                AND %s BETWEEN fecha_inicio AND fecha_fin
            """, (usuario_id, fecha))
            if cursor.fetchone():
                return jsonify({"error": "El profesional tiene la agenda bloqueada en esa fecha"}), 400

            # ✅ Insertar turno si no hay bloqueo
            cursor.execute("""
                INSERT INTO turnos (paciente_id, usuario_id, fecha, motivo)
                VALUES (%s, %s, %s, %s)
            """, (paciente_id, usuario_id, fecha, motivo))
            conn.commit()

            # 🔔 Enviar mail al paciente si tiene email
            cursor.execute("SELECT email, nombre, apellido FROM pacientes WHERE id = %s", (paciente_id,))
            paciente = cursor.fetchone()

            cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", (usuario_id,))
            profesional = cursor.fetchone()

            if paciente and paciente.get("email"):
                try:
                    fecha_dt = datetime.fromisoformat(fecha)
                    fecha_legible = fecha_dt.strftime("%d/%m/%Y")
                    hora_legible = fecha_dt.strftime("%H:%M")
                    msg = Message(
                        subject="Confirmación de turno médico",
                        recipients=[paciente["email"]],
                        body=f"""
Estimado {paciente['nombre']} {paciente['apellido']},

Le confirmamos que su turno ha sido registrado con éxito. A continuación, los detalles:

📅 Fecha: {fecha_legible}
🕒 Hora: {hora_legible} hs
👨‍⚕️ Profesional: {profesional['nombre'] if profesional else 'Asignado'}
📋 Motivo: {motivo}

Por favor, le solicitamos presentarse con 10 minutos de anticipación a su cita.

Muchas gracias,  
Centro Asistencial Universitario
"""
                    )
                    mail.send(msg)
                except Exception as e:
                    print("⚠️ Error enviando mail:", e)

            return jsonify({"message": "Turno creado correctamente ✅"}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()

@bp_turnos.route('/api/turnos/<int:id>', methods=['DELETE'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def eliminar_turno(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM turnos WHERE id=%s", (id,))
    turno = cursor.fetchone()
    if not turno:
        cursor.close()
        conn.close()
        return jsonify({"error": "Turno no encontrado"}), 404

    if current_user.rol == 'profesional' and turno['usuario_id'] != current_user.id:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    cursor.execute("DELETE FROM turnos WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Turno eliminado correctamente ✅"})

@bp_turnos.route('/api/turnos/<int:id>', methods=['PUT'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def editar_turno(id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM turnos WHERE id=%s", (id,))
    turno = cursor.fetchone()
    if not turno:
        cursor.close()
        conn.close()
        return jsonify({"error": "Turno no encontrado"}), 404

    if current_user.rol == 'profesional' and turno['usuario_id'] != current_user.id:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    fecha = data.get("fecha")
    motivo = data.get("motivo")

    cursor.execute("""
        UPDATE turnos
        SET fecha=%s, motivo=%s
        WHERE id=%s
    """, (fecha, motivo, id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Turno actualizado correctamente ✅"})
