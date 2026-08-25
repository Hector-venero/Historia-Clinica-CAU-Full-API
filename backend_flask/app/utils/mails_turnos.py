"""Mails de confirmacion y cancelacion de turnos.

Estaban armados inline dentro de turnos_routes.py, con el HTML mezclado entre
la logica de agenda. Se extraen a un modulo propio para poder tocar las
plantillas sin abrir el archivo de rutas, y para que sobrevivan a los cambios
de esa capa.

El mail de confirmacion adjunta una invitacion iCalendar (.ics) para que el
paciente pueda agendar el turno en un click.
"""

from datetime import datetime, timedelta, timezone

from flask import current_app
from flask_mail import Message

TZ_ARG = timezone(timedelta(hours=-3))

# Datos de contacto que van al pie del mail.
CONTACTO_WHATSAPP = "11 3759-7667"
CONTACTO_TELEFONO = "011 2033-1400 (Int. 6090)"
UBICACION = "Campus Miguelete - UNSAM"
ORGANIZADOR_EMAIL = "no-reply@unsam.edu.ar"

_PIE_CONTACTO = f"""
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
    <p style="font-size: 14px; color: #64748b; line-height: 1.6; margin: 0;">
        <strong>CONTACTO:</strong><br>
        Ante cualquier consulta o para reprogramar, puede contactarnos:<br>
        📱 WhatsApp: {CONTACTO_WHATSAPP}<br>
        📞 Teléfono: {CONTACTO_TELEFONO}
    </p>
    <p style="font-size: 14px; color: #64748b; text-align: center; margin-top: 30px; margin-bottom: 0;">
        Saludos cordiales,<br>
        <strong>Equipo CAU UNSAM</strong>
    </p>
"""


def _envoltura(contenido):
    """Marco comun de los mails: tabla centrada, ancho fijo, estilos inline.

    Los clientes de correo no soportan hojas de estilo externas ni flexbox, de
    ahi la tabla y los estilos inline.
    """
    return f"""
    <div style="background-color: #f4f6f8; padding: 30px 15px; font-family: Arial, sans-serif;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%"
               style="max-width: 600px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;">
            <tr><td style="padding: 30px;">{contenido}</td></tr>
        </table>
    </div>
    """


def _a_datetime(valor):
    """Acepta datetime o texto ISO y devuelve un datetime con zona horaria."""
    if isinstance(valor, datetime):
        dt = valor
    else:
        dt = datetime.fromisoformat(str(valor))
    return dt.replace(tzinfo=TZ_ARG) if dt.tzinfo is None else dt


def _nombre_completo(persona):
    return f"{persona.get('nombre', '')} {persona.get('apellido', '')}".strip()


def construir_ics(paciente, profesional, inicio, fin, motivo):
    """Invitacion iCalendar del turno.

    Las fechas van en UTC (sufijo Z) porque es lo unico que interpretan igual
    todos los clientes de calendario. Los saltos de linea deben ser CRLF por
    RFC 5545: con \\n solo, varios clientes descartan el archivo.
    """
    inicio_dt = _a_datetime(inicio)
    fin_dt = _a_datetime(fin)
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    descripcion = (
        f"Motivo: {motivo or 'Consulta general'}"
        "\\nPor favor asista con 10 minutos de anticipación y su DNI."
    )

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CAU UNSAM//Historia Clinica//ES
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
DTSTAMP:{dtstamp}
UID:turno-{paciente.get('id', '')}-{inicio_dt.strftime('%Y%m%d%H%M')}@cau.unsam.edu.ar
DTSTART:{inicio_dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}
DTEND:{fin_dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}
SUMMARY:Turno Médico - Dr/Dra. {profesional.get('nombre', '')}
DESCRIPTION:{descripcion}
LOCATION:{UBICACION}
STATUS:CONFIRMED
ORGANIZER;CN=CAU UNSAM:mailto:{ORGANIZADOR_EMAIL}
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE;CN={_nombre_completo(paciente)}:mailto:{paciente.get('email', '')}
END:VEVENT
END:VCALENDAR"""
    return ics.replace("\n", "\r\n")


def enviar_confirmacion(paciente, profesional, inicio, fin, motivo=None):
    """Confirma el turno por mail, con la invitacion de calendario adjunta.

    No propaga excepciones: un fallo del servidor de correo no debe impedir que
    el turno quede agendado. Se registra en el log y sigue.
    """
    email = (paciente or {}).get("email")
    if not email:
        return False

    try:
        inicio_dt = _a_datetime(inicio)
        fecha = inicio_dt.strftime("%d/%m/%Y")
        hora = inicio_dt.strftime("%H:%M")
        motivo_txt = motivo or "Consulta general"
        nombre = _nombre_completo(paciente)

        cuerpo = (
            f"Estimado/a {nombre},\n\n"
            "Le confirmamos que su turno ha sido agendado correctamente.\n\n"
            f"DETALLES:\nProfesional: {profesional.get('nombre', '')}\n"
            f"Fecha: {fecha}\nHora: {hora} hs\nMotivo: {motivo_txt}\n\n"
            "Saludos,\nEquipo CAU UNSAM"
        )

        html = _envoltura(f"""
            <h2 style="color: #2563eb; text-align: center; margin-top: 0; margin-bottom: 15px;">Confirmación de Turno Médico</h2>
            <p style="font-size: 16px; color: #333333;">Estimado/a <strong>{nombre}</strong>,</p>
            <p style="font-size: 16px; color: #333333;">Le confirmamos que su turno ha sido agendado correctamente en el <strong>Centro Asistencial Universitario</strong>.</p>

            <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 5px solid #2563eb;">
                <h3 style="margin-top: 0; color: #1e40af; font-size: 18px;">📋 Detalles del Turno</h3>
                <ul style="list-style: none; padding: 0; margin: 0; line-height: 1.8; font-size: 16px; color: #333333;">
                    <li>👨‍⚕️ <strong>Profesional:</strong> {profesional.get('nombre', '')}</li>
                    <li>📅 <strong>Fecha:</strong> {fecha}</li>
                    <li>🕒 <strong>Hora:</strong> {hora} hs</li>
                    <li>💬 <strong>Motivo:</strong> {motivo_txt}</li>
                </ul>
            </div>

            <p style="font-size: 16px; line-height: 1.6; color: #333333;">
            📍 <strong>UBICACIÓN:</strong> {UBICACION}<br>
            ⚠️ <strong>IMPORTANTE:</strong> Por favor, asista con 10 minutos de anticipación y su DNI.</p>
            {_PIE_CONTACTO}
        """)

        mensaje = Message(
            subject=f"Confirmación de turno médico - Dr/Dra. {profesional.get('nombre', '')}",
            recipients=[email],
            body=cuerpo,
            html=html,
        )
        mensaje.attach(
            "invitacion_turno.ics",
            "text/calendar",
            construir_ics(paciente, profesional, inicio, fin, motivo).encode("utf-8"),
        )
        current_app.extensions["mail"].send(mensaje)
        return True
    except Exception:
        current_app.logger.exception("No se pudo enviar el mail de confirmación del turno")
        return False


def enviar_cancelacion(paciente, profesional_nombre, inicio):
    """Avisa por mail que el turno fue cancelado. Tampoco propaga excepciones."""
    email = (paciente or {}).get("email")
    if not email:
        return False

    try:
        inicio_dt = _a_datetime(inicio)
        fecha = inicio_dt.strftime("%d/%m/%Y")
        hora = inicio_dt.strftime("%H:%M")
        nombre = _nombre_completo(paciente)

        cuerpo = (
            f"Estimado/a {nombre},\n\n"
            "Le informamos que su turno ha sido CANCELADO.\n\n"
            f"DATOS DEL TURNO CANCELADO:\nProfesional: {profesional_nombre}\n"
            f"Fecha: {fecha}\nHora: {hora} hs\n\n"
            "Saludos,\nEquipo CAU UNSAM"
        )

        html = _envoltura(f"""
            <h2 style="color: #dc2626; text-align: center; margin-top: 0; margin-bottom: 15px;">Cancelación de Turno Médico</h2>
            <p style="font-size: 16px; color: #333333;">Estimado/a <strong>{nombre}</strong>,</p>
            <p style="font-size: 16px; color: #333333;">Le informamos que su turno ha sido <strong>CANCELADO</strong>.</p>

            <div style="background-color: #fef2f2; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 5px solid #dc2626;">
                <h3 style="margin-top: 0; color: #991b1b; font-size: 18px;">❌ Datos del turno cancelado</h3>
                <ul style="list-style: none; padding: 0; margin: 0; line-height: 1.8; font-size: 16px; color: #333333;">
                    <li>👨‍⚕️ <strong>Profesional:</strong> {profesional_nombre}</li>
                    <li>📅 <strong>Fecha:</strong> {fecha}</li>
                    <li>🕒 <strong>Hora:</strong> {hora} hs</li>
                </ul>
            </div>

            <p style="font-size: 16px; line-height: 1.6; color: #333333;">Si usted no solicitó esta cancelación o desea reprogramar un nuevo turno, por favor ingrese al sistema o comuníquese con nosotros.</p>
            {_PIE_CONTACTO}
        """)

        current_app.extensions["mail"].send(
            Message(
                subject=f"Cancelación de turno médico - Dr/Dra. {profesional_nombre}",
                recipients=[email],
                body=cuerpo,
                html=html,
            )
        )
        return True
    except Exception:
        current_app.logger.exception("No se pudo enviar el mail de cancelación del turno")
        return False
