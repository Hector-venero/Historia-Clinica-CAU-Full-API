# backend_flask/app/utils/alertas.py

import datetime
from flask import current_app
from flask_mail import Message
from app.database import db_cursor

DIAS_ESPANOL = {
    0: 'Lunes',
    1: 'Martes',
    2: 'Miercoles',
    3: 'Jueves',
    4: 'Viernes',
    5: 'Sabado',
    6: 'Domingo'
}

def obtener_agenda_manana(usuario_id, fecha_manana):
    """
    Obtiene los turnos individuales y grupales de un profesional para la fecha dada.
    """
    with db_cursor() as (_conn, cursor):
        # Turnos individuales del profesional
        cursor.execute(
            """
            SELECT t.fecha_inicio, t.fecha_fin, t.motivo, t.observaciones, p.nombre, p.apellido
            FROM turnos t
            JOIN pacientes p ON t.paciente_id = p.id
            WHERE t.usuario_id = %s AND DATE(t.fecha_inicio) = %s
            ORDER BY t.fecha_inicio ASC
            """,
            (usuario_id, fecha_manana),
        )
        turnos_individuales = cursor.fetchall()

        # Turnos de los grupos que integra
        cursor.execute(
            """
            SELECT tg.fecha_inicio, tg.fecha_fin, tg.observaciones, gp.nombre AS grupo_nombre
            FROM turnos_grupales tg
            JOIN grupos_profesionales gp ON tg.grupo_id = gp.id
            JOIN grupo_miembros gm ON gp.id = gm.grupo_id
            WHERE gm.usuario_id = %s AND DATE(tg.fecha_inicio) = %s
            ORDER BY tg.fecha_inicio ASC
            """,
            (usuario_id, fecha_manana),
        )
        turnos_grupales = cursor.fetchall()

    return turnos_individuales, turnos_grupales

def generar_html_correo(nombre_profesional, fecha_str, turnos_ind, turnos_grup):
    """
    Genera el cuerpo HTML del correo de alertas de turnos.
    """
    frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost')
    
    # Encabezado
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h2 style="color: #1976D2; border-bottom: 2px solid #1976D2; padding-bottom: 10px;">Hola, {nombre_profesional}</h2>
            <p style="font-size: 16px;">Este es el resumen de tu agenda para mañana, <strong>{fecha_str}</strong>.</p>
    """
    
    # Si no hay ningún turno de ningún tipo
    if not turnos_ind and not turnos_grup:
        html += f"""
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #9e9e9e;">
                <p style="margin: 0; font-size: 15px; color: #666666;">No tenés turnos programados para mañana, pero recordá que figurás disponible en el sistema.</p>
            </div>
        """
    else:
        # Turnos individuales
        if turnos_ind:
            html += """
            <h3 style="color: #007AFF; margin-top: 25px;">📋 Turnos Individuales</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #f5f5f5; text-align: left;">
                        <th style="padding: 10px; border-bottom: 1px solid #ddd;">Horario</th>
                        <th style="padding: 10px; border-bottom: 1px solid #ddd;">Paciente</th>
                        <th style="padding: 10px; border-bottom: 1px solid #ddd;">Motivo / Obs</th>
                    </tr>
                </thead>
                <tbody>
            """
            for t in turnos_ind:
                hora_ini = t['fecha_inicio'].strftime('%H:%M')
                hora_fin = t['fecha_fin'].strftime('%H:%M')
                obs_str = f" - Obs: {t['observaciones']}" if t.get('observaciones') else ""
                html += f"""
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">{hora_ini} - {hora_fin}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{t['nombre']} {t['apellido']}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee; color: #555;">{t['motivo'] or 'Sin motivo'}{obs_str}</td>
                    </tr>
                """
            html += "</tbody></table>"
            
        # Turnos grupales
        if turnos_grup:
            # Agrupar turnos grupales repetidos en el mismo bloque para evitar duplicados en el mail
            bloques_grupales = {}
            for tg in turnos_grup:
                clave = (tg['fecha_inicio'], tg['fecha_fin'], tg.get('grupo_nombre'))
                if clave not in bloques_grupales:
                    bloques_grupales[clave] = tg['observaciones']
            
            html += """
            <h3 style="color: #00936B; margin-top: 25px;">👥 Turnos Grupales / Rehabilitación</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #f5f5f5; text-align: left;">
                        <th style="padding: 10px; border-bottom: 1px solid #ddd;">Horario</th>
                        <th style="padding: 10px; border-bottom: 1px solid #ddd;">Grupo / Área</th>
                        <th style="padding: 10px; border-bottom: 1px solid #ddd;">Observaciones</th>
                    </tr>
                </thead>
                <tbody>
            """
            for (f_ini, f_fin, grupo_nom), obs in bloques_grupales.items():
                hora_ini = f_ini.strftime('%H:%M')
                hora_fin = f_fin.strftime('%H:%M')
                html += f"""
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">{hora_ini} - {hora_fin}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">Grupo: {grupo_nom}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee; color: #555;">{obs or 'Sin observaciones'}</td>
                    </tr>
                """
            html += "</tbody></table>"
            
    # Pie de página
    html += f"""
            <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 30px 0;">
            <p style="font-size: 13px; color: #666; text-align: center;">
                Si necesitás realizar algún cambio en tu agenda o consultar la ficha de un paciente, ingresá a la plataforma:
            </p>
            <p style="text-align: center; margin-top: 15px;">
                <a href="{frontend_url}" style="background-color: #1976D2; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                    Ir al Sistema de Historias Clínicas CAU
                </a>
            </p>
            <p style="font-size: 11px; color: #999; text-align: center; margin-top: 30px; border-top: 1px dashed #e0e0e0; padding-top: 10px;">
                Este es un correo automático generado por el sistema. Por favor no lo respondas.
            </p>
        </div>
    </body>
    </html>
    """
    return html

def procesar_y_enviar_alertas(dry_run=False):
    """
    Función principal llamada desde CLI para buscar profesionales disponibles mañana
    y enviarles el resumen de turnos.
    """
    from app import mail
    
    # Calcular mañana
    manana = datetime.date.today() + datetime.timedelta(days=1)
    dia_semana_num = manana.weekday()
    dia_nombre = DIAS_ESPANOL[dia_semana_num]
    fecha_bonita = manana.strftime('%d/%m/%Y')
    fecha_con_dia = f"{dia_nombre} {fecha_bonita}"
    
    current_app.logger.info(f"Iniciando proceso de alertas de turnos para: {fecha_con_dia}")
    
    # 1. Obtener profesionales disponibles mañana
    profesionales = []
    try:
        with db_cursor() as (_conn, cursor):
            # Profesionales activos con disponibilidad activa para el dia de manana.
            # d.dia_semana viene sin tilde, igual que el ENUM: con "Miercoles"
            # acentuado esta comparacion no matchearia nunca y nadie recibiria
            # el aviso los miercoles.
            cursor.execute(
                """
                SELECT DISTINCT u.id, u.nombre, u.email
                FROM usuarios u
                JOIN disponibilidades d ON u.id = d.usuario_id
                WHERE u.activo = 1 AND d.dia_semana = %s AND d.activo = 1
                """,
                (dia_nombre,),
            )
            profesionales = cursor.fetchall()
    except Exception as e:
        current_app.logger.exception("Error al buscar profesionales disponibles: %s", e)
        return {"profesionales": 0, "enviados": 0, "simulados": 0, "errores": 1}
        
    current_app.logger.info(f"Se encontraron {len(profesionales)} profesionales disponibles para mañana ({dia_nombre}).")
    
    enviados_ok = 0
    enviados_error = 0
    simulados = 0
    
    for prof in profesionales:
        try:
            u_id = prof['id']
            email = prof['email']
            nombre = prof['nombre']
            
            # Obtener agenda
            turnos_ind, turnos_grup = obtener_agenda_manana(u_id, manana)
            
            # Construir mail
            html_body = generar_html_correo(nombre, fecha_con_dia, turnos_ind, turnos_grup)
            
            msg = Message(
                subject=f"[CAU] Agenda de Turnos - Mañana {fecha_bonita}",
                recipients=[email],
                html=html_body
            )
            
            # Texto plano alternativo
            msg.body = f"Hola {nombre}.\n\nEste es el resumen de tu agenda para mañana {fecha_con_dia}.\n\n"
            if not turnos_ind and not turnos_grup:
                msg.body += "No tenés turnos programados para mañana.\n"
            else:
                if turnos_ind:
                    msg.body += "📋 Turnos Individuales:\n"
                    for t in turnos_ind:
                        msg.body += f"- {t['fecha_inicio'].strftime('%H:%M')} - {t['fecha_fin'].strftime('%H:%M')}: {t['nombre']} {t['apellido']} ({t['motivo'] or 'Sin motivo'})\n"
                if turnos_grup:
                    msg.body += "\n👥 Turnos Grupales / Rehabilitación:\n"
                    for tg in turnos_grup:
                        msg.body += f"- {tg['fecha_inicio'].strftime('%H:%M')} - {tg['fecha_fin'].strftime('%H:%M')}: Grupo: {tg['grupo_nombre']}\n"
            
            if dry_run:
                simulados += 1
                current_app.logger.info(f"Alerta simulada para: {email}")
            else:
                mail.send(msg)
                enviados_ok += 1
                current_app.logger.info(f"Alerta enviada correctamente a: {email}")
            
        except Exception as ex:
            enviados_error += 1
            current_app.logger.error(f"Error al enviar alerta a {prof.get('email')}: {str(ex)}")
            
    current_app.logger.info(f"Proceso finalizado. Enviados correctamente: {enviados_ok}. Errores: {enviados_error}.")
    return {
        "profesionales": len(profesionales),
        "enviados": enviados_ok,
        "simulados": simulados,
        "errores": enviados_error,
    }
