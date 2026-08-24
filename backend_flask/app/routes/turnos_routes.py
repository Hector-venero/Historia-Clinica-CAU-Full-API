from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from app.database import get_connection, db_cursor
from app.utils.permisos import requiere_rol
from app import mail
from flask_mail import Message

bp_turnos = Blueprint("turnos", __name__)

# Timezone Argentina FIX
TZ_ARG = timezone(timedelta(hours=-3))

# ==========================================================
#  Función auxiliar: Verificar disponibilidad del médico
# ==========================================================
def medico_disponible(usuario_id, fecha_inicio, fecha_fin):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Primero averiguamos qué ROL tiene este usuario
    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
    user_data = cursor.fetchone()
    es_area = user_data and user_data['rol'] == 'area'

    inicio = datetime.fromisoformat(fecha_inicio)
    fin = datetime.fromisoformat(fecha_fin)

    hora_ini = inicio.strftime("%H:%M:%S")
    hora_fin = fin.strftime("%H:%M:%S")

    # ... (lógica de dias de semana igual que antes) ...
    dia_semana = inicio.strftime("%A")
    dias = { "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo" }
    dia_es = dias.get(dia_semana, "Lunes")

    # 2. Chequeamos si TRABAJA ese día (Disponibilidad) - ESTO SIEMPRE SE CHEQUEA
    cursor.execute("""
        SELECT 1 FROM disponibilidades
        WHERE usuario_id = %s
        AND dia_semana = %s
        AND %s >= hora_inicio
        AND %s <= hora_fin
        AND activo = 1
    """, (usuario_id, dia_es, hora_ini, hora_fin))
    disponible = cursor.fetchone()

    # 3. Chequeamos AUSENCIAS (Vacaciones) - ESTO SIEMPRE SE CHEQUEA
    cursor.execute("""
        SELECT 1 FROM ausencias
        WHERE usuario_id = %s
        AND (%s BETWEEN fecha_inicio AND fecha_fin
        OR  %s BETWEEN fecha_inicio AND fecha_fin)
    """, (usuario_id, fecha_inicio, fecha_fin))
    ausente = cursor.fetchone()

    # 4. Chequeamos SOLAPAMIENTO (Ocupado)
    # SI ES AREA -> NO CHEQUEAMOS ESTO (puede tener infinitos turnos)
    ocupado = None
    if not es_area:
        cursor.execute("""
           SELECT 1 FROM turnos
            WHERE usuario_id = %s
            AND (
                (fecha_inicio < %s AND fecha_fin > %s)
                OR
                (fecha_inicio < %s AND fecha_fin > %s)
            )
        """, (usuario_id, fecha_fin, fecha_inicio, fecha_inicio, fecha_fin))
        ocupado = cursor.fetchone()
    
    cursor.close()
    conn.close()

    # Si es area, 'ocupado' siempre es None (False), así que permite solapamiento
    return bool(disponible) and not ausente and not ocupado

# ==========================================================
#  Rutas de Turnos
# ==========================================================
@bp_turnos.route('/api/turnos', methods=['GET', 'POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area') 
def api_turnos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        
        if current_user.rol in ['profesional', 'area']:
            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.nombre, p.dni, u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON t.paciente_id = p.id
                JOIN usuarios u ON t.usuario_id = u.id
                WHERE t.usuario_id = %s
                ORDER BY t.fecha_inicio ASC
            """, (current_user.id,))
        else:
            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.nombre, p.dni, u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON t.paciente_id = p.id
                JOIN usuarios u ON t.usuario_id = u.id
                ORDER BY t.fecha_inicio ASC
            """)

        turnos = cursor.fetchall()
        cursor.close()
        conn.close()

        eventos = [{
            "id": t["id"],
            "paciente": t["nombre"],
            "dni": t["dni"],
            "start": t["fecha_inicio"].replace(tzinfo=TZ_ARG).isoformat(),
            "end": t["fecha_fin"].replace(tzinfo=TZ_ARG).isoformat(),
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
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")
        motivo = data.get("motivo")

        if not (paciente_id and usuario_id and fecha_inicio and fecha_fin):
            return jsonify({"error": "Campos obligatorios faltantes"}), 400

        if current_user.rol == 'profesional' and usuario_id != current_user.id:
            return jsonify({"error": "No puede asignar turnos a otros profesionales"}), 403
        
        try:
            if not medico_disponible(usuario_id, fecha_inicio, fecha_fin):
                return jsonify({"error": "El profesional no está disponible en esa fecha u horario"}), 400

            cursor.execute("""
                INSERT INTO turnos (paciente_id, usuario_id, fecha_inicio, fecha_fin, motivo)
                VALUES (%s, %s, %s, %s, %s)
            """, (paciente_id, usuario_id, fecha_inicio, fecha_fin, motivo))
            conn.commit()

            cursor.execute("SELECT email, nombre, apellido FROM pacientes WHERE id = %s", (paciente_id,))
            paciente = cursor.fetchone()

            cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", (usuario_id,))
            profesional = cursor.fetchone()

            if paciente and paciente.get("email"):
                try:
                    fecha_dt = datetime.fromisoformat(fecha_inicio).replace(tzinfo=TZ_ARG)
                    fecha_legible = fecha_dt.strftime("%d/%m/%Y")
                    hora_legible = fecha_dt.strftime("%H:%M")

                    # Generar fechas en formato UTC para el iCalendar
                    fecha_fin_dt = datetime.fromisoformat(fecha_fin).replace(tzinfo=TZ_ARG)
                    gcal_start = fecha_dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    gcal_end = fecha_fin_dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

                    # Generar archivo de invitación .ics (iCalendar)
                    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CAU UNSAM//Historia Clinica//ES
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
DTSTAMP:{dtstamp}
UID:turno-{paciente_id}-{fecha_dt.strftime("%Y%m%d%H%M")}@cau.unsam.edu.ar
DTSTART:{gcal_start}
DTEND:{gcal_end}
SUMMARY:Turno Médico - Dr/Dra. {profesional['nombre']}
DESCRIPTION:Motivo: {motivo if motivo else 'Consulta general'}\\nPor favor asista con 10 minutos de anticipación y su DNI.
LOCATION:Campus Miguelete - UNSAM
STATUS:CONFIRMED
ORGANIZER;CN=CAU UNSAM:mailto:no-reply@unsam.edu.ar
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE;CN={paciente['nombre']} {paciente['apellido']}:mailto:{paciente['email']}
END:VEVENT
END:VCALENDAR""".replace('\n', '\r\n')

                    # Fallback en texto plano (por si el cliente de correo no soporta HTML)
                    msg_body = f"Estimado/a {paciente['nombre']} {paciente['apellido']},\n\nLe confirmamos que su turno ha sido agendado correctamente.\n\nDETALLES:\nProfesional: {profesional['nombre']}\nFecha: {fecha_legible}\nHora: {hora_legible} hs\nMotivo: {motivo if motivo else 'Consulta general'}\n\nSaludos,\nEquipo CAU UNSAM"
                    
                    # Plantilla HTML estética
                    msg_html = f"""
                    <div style="background-color: #f4f6f8; padding: 30px 15px; font-family: Arial, sans-serif;">
                        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;">
                            <tr>
                                <td style="padding: 30px;">
                                    <h2 style="color: #2563eb; text-align: center; margin-top: 0; margin-bottom: 15px;">Confirmación de Turno Médico</h2>
                                    <p style="font-size: 16px; color: #333333;">Estimado/a <strong>{paciente['nombre']} {paciente['apellido']}</strong>,</p>
                                    <p style="font-size: 16px; color: #333333;">Le confirmamos que su turno ha sido agendado correctamente en el <strong>Centro Asistencial Universitario</strong>.</p>
                                    
                                    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 5px solid #2563eb;">
                                        <h3 style="margin-top: 0; color: #1e40af; font-size: 18px;">📋 Detalles del Turno</h3>
                                        <ul style="list-style: none; padding: 0; margin: 0; line-height: 1.8; font-size: 16px; color: #333333;">
                                            <li>👨‍⚕️ <strong>Profesional:</strong> {profesional['nombre']}</li>
                                            <li>📅 <strong>Fecha:</strong> {fecha_legible}</li>
                                            <li>🕒 <strong>Hora:</strong> {hora_legible} hs</li>
                                            <li>💬 <strong>Motivo:</strong> {motivo if motivo else 'Consulta general'}</li>
                                        </ul>
                                    </div>

                                    <p style="font-size: 16px; line-height: 1.6; color: #333333;">
                                    📍 <strong>UBICACIÓN:</strong> Campus Miguelete - UNSAM<br>
                                    ⚠️ <strong>IMPORTANTE:</strong> Por favor, asista con 10 minutos de anticipación y su DNI.</p>

                                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                                    <p style="font-size: 14px; color: #64748b; line-height: 1.6; margin: 0;">
                                        <strong>CONTACTO:</strong><br>
                                        Ante cualquier consulta o para reprogramar, puede contactarnos:<br>
                                        📱 WhatsApp: 11 3759-7667<br>
                                        📞 Teléfono: 011 2033-1400 (Int. 6090)
                                    </p>
                                    <p style="font-size: 14px; color: #64748b; text-align: center; margin-top: 30px; margin-bottom: 0;">
                                        Saludos cordiales,<br>
                                        <strong>Equipo CAU UNSAM</strong>
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </div>
                    """

                    msg = Message(
                        subject=f"Confirmación de turno médico - Dr/Dra. {profesional['nombre']}",
                        recipients=[paciente["email"]],
                        body=msg_body,
                        html=msg_html
                    )
                    
                    # Adjuntar el archivo de calendario al correo
                    msg.attach("invitacion_turno.ics", "text/calendar", ics_content.encode('utf-8'))
                    
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

# ==========================================================
#  Eliminar turno
# ==========================================================
@bp_turnos.route('/api/turnos/<int:id>', methods=['DELETE'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def eliminar_turno(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener info del turno antes de borrar
    cursor.execute("""
        SELECT t.usuario_id, t.paciente_id, t.fecha_inicio, t.fecha_fin, u.nombre AS profesional
        FROM turnos t
        JOIN usuarios u ON u.id = t.usuario_id
        WHERE t.id = %s
    """, (id,))
    turno = cursor.fetchone()

    if not turno:
        cursor.close()
        conn.close()
        return jsonify({"error": "Turno no encontrado"}), 404

    # Validación: profesionales solo pueden borrar sus propios turnos
    if current_user.rol == 'profesional' and turno['usuario_id'] != current_user.id:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    # Consulta del paciente
    cursor.execute("SELECT nombre, apellido, email FROM pacientes WHERE id=%s", (turno["paciente_id"],))
    paciente = cursor.fetchone()

    # Proceder a eliminar
    cursor.execute("DELETE FROM turnos WHERE id=%s", (id,))
    conn.commit()

    # Enviar mail si el paciente tiene email
    if paciente and paciente.get("email"):
        try:
            fecha_dt = turno["fecha_inicio"].replace(tzinfo=TZ_ARG)
            fecha_legible = fecha_dt.strftime("%d/%m/%Y")
            hora_legible = fecha_dt.strftime("%H:%M")

            msg_body = f"Estimado/a {paciente['nombre']} {paciente['apellido']},\n\nLe informamos que su turno ha sido CANCELADO.\n\nDATOS DEL TURNO CANCELADO:\nProfesional: {turno['profesional']}\nFecha: {fecha_legible}\nHora: {hora_legible} hs\n\nSaludos,\nEquipo CAU UNSAM"

            msg_html  = f"""
            <div style="background-color: #f4f6f8; padding: 30px 15px; font-family: Arial, sans-serif;">
                <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;">
                    <tr>
                        <td style="padding: 30px;">
                            <h2 style="color: #dc2626; text-align: center; margin-top: 0; margin-bottom: 15px;">Cancelación de Turno Médico</h2>
                            <p style="font-size: 16px; color: #333333;">Estimado/a <strong>{paciente['nombre']} {paciente['apellido']}</strong>,</p>
                            <p style="font-size: 16px; color: #333333;">Le informamos que su turno ha sido <strong>CANCELADO</strong>.</p>
                            
                            <div style="background-color: #fef2f2; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 5px solid #dc2626;">
                                <h3 style="margin-top: 0; color: #991b1b; font-size: 18px;">❌ Datos del turno cancelado</h3>
                                <ul style="list-style: none; padding: 0; margin: 0; line-height: 1.8; font-size: 16px; color: #333333;">
                                    <li>👨‍⚕️ <strong>Profesional:</strong> {turno['profesional']}</li>
                                    <li>📅 <strong>Fecha:</strong> {fecha_legible}</li>
                                    <li>🕒 <strong>Hora:</strong> {hora_legible} hs</li>
                                </ul>
                            </div>

                            <p style="font-size: 16px; line-height: 1.6; color: #333333;">Si usted no solicitó esta cancelación o desea reprogramar un nuevo turno, por favor ingrese al sistema o comuníquese con nosotros.</p>

                            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                            <p style="font-size: 14px; color: #64748b; line-height: 1.6; margin: 0;">
                                <strong>CANALES DE ATENCIÓN:</strong><br>
                                📱 WhatsApp: 11 3759-7667<br>
                                📞 Teléfono: 011 2033-1400 (Int. 6090)
                            </p>
                            <p style="font-size: 14px; color: #64748b; text-align: center; margin-top: 30px; margin-bottom: 0;">
                                Saludos cordiales,<br>
                                <strong>Equipo CAU UNSAM</strong>
                            </p>
                        </td>
                    </tr>
                </table>
            </div>
            """
            msg = Message(
                subject=f"Cancelación de turno médico - Dr/Dra. {turno['profesional']}",
                recipients=[paciente["email"]],
                body=msg_body,
                html=msg_html
            )
            mail.send(msg)
        except Exception as e:
            print("⚠️ Error enviando mail de cancelación:", e)

    cursor.close()
    conn.close()
    return jsonify({"message": "Turno eliminado correctamente y mail enviado 📧"})


# ==========================================================
# Editar turno
# ==========================================================
@bp_turnos.route('/api/turnos/<int:id>', methods=['PUT'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def editar_turno(id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    # Los returns tempranos por "falta fecha" y "sin duracion configurada"
    # salian sin cerrar la conexion: cada request invalido filtraba una.
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT usuario_id FROM turnos WHERE id=%s", (id,))
        turno = cursor.fetchone()
        if not turno:
            return jsonify({"error": "Turno no encontrado"}), 404

        if current_user.rol == 'profesional' and turno['usuario_id'] != current_user.id:
            return jsonify({"error": "No autorizado"}), 403

        motivo = data.get("motivo")

        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")

        if not fecha_inicio or not fecha_fin:
            nueva_fecha = data.get("fecha")
            if not nueva_fecha:
                return jsonify({"error": "Falta fecha"}), 400

            cursor.execute("SELECT duracion_turno FROM usuarios WHERE id=%s", (turno['usuario_id'],))
            info_prof = cursor.fetchone()

            if not info_prof or not info_prof["duracion_turno"]:
                return jsonify({"error": "El profesional no tiene duración de turno configurada"}), 400

            duracion = info_prof["duracion_turno"]

            inicio_dt = datetime.fromisoformat(nueva_fecha)
            fin_dt = inicio_dt + timedelta(minutes=duracion)

            fecha_inicio = inicio_dt.isoformat()
            fecha_fin = fin_dt.isoformat()

        cursor.execute("""
            UPDATE turnos
            SET fecha_inicio=%s, fecha_fin=%s, motivo=%s
            WHERE id=%s
        """, (fecha_inicio, fecha_fin, motivo, id))

        conn.commit()

    return jsonify({"message": "Turno actualizado correctamente ✅"})


# ==========================================================
#  Crear tanda de turnos
# ==========================================================
@bp_turnos.route('/api/turnos/tanda', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def crear_turnos_tanda():
    try:
        data = request.get_json()
        paciente_id = data.get("paciente_id")
        usuario_id = data.get("usuario_id")
        motivo = data.get("motivo", "")
        fecha_inicial = datetime.fromisoformat(data.get("fecha"))
        cantidad = int(data.get("cantidad", 1))
        dias_semana = data.get("dias_semana", [])

        if not (paciente_id and usuario_id and fecha_inicial and dias_semana):
            return jsonify({"error": "Faltan datos requeridos"}), 400

        if current_user.rol == 'profesional' and usuario_id != current_user.id:
            return jsonify({"error": "No puede asignar turnos a otros profesionales"}), 403

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT duracion_turno FROM usuarios WHERE id=%s", (usuario_id,))
        profesional = cursor.fetchone()

        if not profesional or not profesional["duracion_turno"]:
            return jsonify({"error": "El profesional no tiene duración de turno configurada"}), 400

        dur = profesional["duracion_turno"]

        dias_map = {
            "Lunes": 0,
            "Martes": 1,
            "Miércoles": 2,
            "Jueves": 3,
            "Viernes": 4,
            "Sábado": 5,
            "Domingo": 6
        }
        dias_indices = [dias_map[d] for d in dias_semana if d in dias_map]

        turnos_creados = 0
        fecha_actual = fecha_inicial

        while turnos_creados < cantidad:
            if fecha_actual.weekday() in dias_indices:

                fecha_fin = fecha_actual + timedelta(minutes=dur)

                if not medico_disponible(usuario_id, fecha_actual.isoformat(), fecha_fin.isoformat()):
                    fecha_actual += timedelta(days=1)
                    continue

                cursor.execute("""
                    INSERT INTO turnos (paciente_id, usuario_id, fecha_inicio, fecha_fin, motivo)
                    VALUES (%s, %s, %s, %s, %s)
                """, (paciente_id, usuario_id, fecha_actual, fecha_fin, motivo))

                turnos_creados += 1

            fecha_actual += timedelta(days=1)

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": f"Se crearon {turnos_creados} turnos correctamente ✅"}), 201

    except Exception as e:
        print("Error al crear tanda de turnos:", e)
        return jsonify({"error": "Error al crear tanda de turnos"}), 500


# ==========================================================
#  Turnos por grupo
# ==========================================================
@bp_turnos.route("/api/turnos/profesional/<int:usuario_id>", methods=["GET"])
@login_required
def turnos_profesional(usuario_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            t.id,
            t.fecha_inicio,
            t.fecha_fin,
            t.motivo,
            p.nombre AS paciente,
            p.dni,
            u.nombre AS profesional,
            '#007AFF' AS color   
        FROM turnos t
        JOIN pacientes p ON t.paciente_id = p.id
        JOIN usuarios u ON t.usuario_id = u.id
        WHERE u.id = %s
    """, (usuario_id,))

    individuales = cursor.fetchall()

    cursor.execute("SELECT grupo_id FROM grupo_miembros WHERE usuario_id = %s", (usuario_id,))
    grupos = [g["grupo_id"] for g in cursor.fetchall()]

    grupales = []
    if grupos:
        cursor.execute(f"""
            SELECT 
                t.id,
                t.fecha_inicio,
                t.fecha_fin,
                t.motivo,
                p.nombre AS paciente,
                p.dni,
                u.nombre AS profesional,
                gp.color
            FROM turnos t
            JOIN pacientes p ON t.paciente_id = p.id
            JOIN usuarios u ON t.usuario_id = u.id
            JOIN grupo_miembros gm ON gm.usuario_id = u.id
            JOIN grupos_profesionales gp ON gp.id = gm.grupo_id
            WHERE gm.grupo_id IN ({','.join(['%s'] * len(grupos))})
        """, grupos)

        grupales = cursor.fetchall()

    cursor.close()
    conn.close()

    def to_event(t):
        return {
            "id": t["id"],
            "title": f"{t['paciente']} ({t['profesional']})",
            "start": t["fecha_inicio"].replace(tzinfo=TZ_ARG).isoformat(),
            "end": t["fecha_fin"].replace(tzinfo=TZ_ARG).isoformat(),
            "paciente": t["paciente"],
            "dni": t["dni"],
            "profesional": t["profesional"],
            "description": t["motivo"],
            "backgroundColor": t["color"],
            "borderColor": t["color"],
        }

    return jsonify([to_event(t) for t in individuales] + [to_event(t) for t in grupales])


# =========================================================
#  Turnos completos del profesional (individuales + grupales)
# =========================================================
@bp_turnos.route("/api/turnos/profesional/completo", methods=["GET"])
@login_required
def turnos_profesional_completo():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    es_director = current_user.rol == "director"

    #  SI ES DIRECTOR → TRAE TODOS LOS TURNOS
    if es_director:
        cursor.execute("""
            SELECT
                t.id,
                t.fecha_inicio AS start,
                t.fecha_fin AS end,
                p.nombre AS paciente,
                p.dni,
                u.nombre AS profesional,
                t.motivo AS description,
                '#1976D2' AS color,
                1 AS editable
            FROM turnos t
            JOIN pacientes p ON p.id = t.paciente_id
            JOIN usuarios u ON u.id = t.usuario_id
            ORDER BY t.fecha_inicio ASC
        """)
        turnos = cursor.fetchall()
        cursor.close()
        conn.close()

        def fix(t):
            t["start"] = t["start"].replace(tzinfo=TZ_ARG).isoformat()
            t["end"] = t["end"].replace(tzinfo=TZ_ARG).isoformat()
            return t

        return jsonify([fix(t) for t in turnos])

    #  SI ES PROFESIONAL → SOLO SUS TURNOS (actúa igual)
    usuario_id = current_user.id

    cursor.execute("""
        SELECT
            t.id,
            t.fecha_inicio AS start,
            t.fecha_fin AS end,
            p.nombre AS paciente,
            p.dni,
            u.nombre AS profesional,
            t.motivo AS description,
            '#1976D2' AS color,
            1 AS editable
        FROM turnos t
        JOIN pacientes p ON p.id = t.paciente_id
        JOIN usuarios u ON u.id = t.usuario_id
        WHERE t.usuario_id = %s
    """, (usuario_id,))
    individuales = cursor.fetchall()

    cursor.execute("""
        SELECT grupo_id FROM grupo_miembros WHERE usuario_id = %s
    """, (usuario_id,))
    grupos_ids = [g["grupo_id"] for g in cursor.fetchall()]

    grupales = []
    if grupos_ids:
        cursor.execute(f"""
            SELECT
                t.id,
                t.fecha_inicio AS start,
                t.fecha_fin AS end,
                p.nombre AS paciente,
                p.dni,
                u.nombre AS profesional,
                t.motivo AS description,
                gp.color AS color,
                1 AS editable
            FROM turnos t
            JOIN pacientes p ON p.id = t.paciente_id
            JOIN usuarios u ON u.id = t.usuario_id
            JOIN grupo_miembros gm ON gm.usuario_id = u.id
            JOIN grupos_profesionales gp ON gp.id = gm.grupo_id
            WHERE gm.grupo_id IN ({','.join(['%s'] * len(grupos_ids))})
        """, tuple(grupos_ids))
        grupales = cursor.fetchall()

    cursor.close()
    conn.close()

    def fix(t):
        t["start"] = t["start"].replace(tzinfo=TZ_ARG).isoformat()
        t["end"] = t["end"].replace(tzinfo=TZ_ARG).isoformat()
        return t

    return jsonify([fix(t) for t in individuales] + [fix(t) for t in grupales])

# ==========================================================
#  Turnos por grupo
# ==========================================================
@bp_turnos.route('/api/turnos/grupo/<int:grupo_id>', methods=['GET'])
@login_required
def turnos_por_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            t.id,
            t.fecha_inicio AS start,
            t.fecha_fin AS end,
            t.motivo AS description,
            p.nombre AS paciente,
            p.dni,
            u.nombre AS profesional,
            gp.color
        FROM grupo_miembros gm
        JOIN turnos t ON gm.usuario_id = t.usuario_id
        JOIN pacientes p ON p.id = t.paciente_id
        JOIN usuarios u ON u.id = t.usuario_id
        JOIN grupos_profesionales gp ON gp.id = gm.grupo_id
        WHERE gm.grupo_id = %s
        ORDER BY t.fecha_inicio ASC
    """, (grupo_id,))

    turnos = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([
        {
            "id": t["id"],
            "paciente": t["paciente"],
            "dni": t["dni"],
            "profesional": t["profesional"],
            "description": t["description"],
            "start": t["start"].replace(tzinfo=TZ_ARG).isoformat(),
            "end": t["end"].replace(tzinfo=TZ_ARG).isoformat(),
            "color": t["color"]
        }
        for t in turnos
    ])
