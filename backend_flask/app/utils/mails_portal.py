"""Correos del portal del paciente: verificacion, bienvenida y aviso de envio.

Mismo patron que el resto: arman el Message y lo devuelven; None si no hay
remitente configurado, para que no poder mandar un correo no rompa la operacion.
"""

from flask import current_app
from flask_mail import Message

from app import marca

_ESTILO_BOTON = (
    "display:inline-block;background:#0d9488;color:#ffffff;text-decoration:none;"
    "padding:14px 28px;border-radius:10px;font-weight:600;font-size:16px;"
)


def _remitente():
    return current_app.config.get("MAIL_DEFAULT_SENDER")


def mail_verificacion_paciente(destinatario, nombre, token, url_portal):
    remitente = _remitente()
    if not remitente or not destinatario:
        return None

    enlace = f"{url_portal}/verificar/{token}"

    cuerpo = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color:#0f172a;">
        <h2 style="margin:0 0 16px;">Confirmá tu correo</h2>
        <p style="font-size:15px; line-height:1.6; margin:0 0 24px;">
            Hola {nombre}. Hacé clic para activar tu cuenta y ver los estudios y recetas
            que te envían tus profesionales.
        </p>
        <p style="margin:0 0 28px;">
            <a href="{enlace}" style="{_ESTILO_BOTON}">Activar mi cuenta</a>
        </p>
        <p style="font-size:13px; color:#64748b; line-height:1.6; margin:0;">
            El enlace vence en 48 horas.<br>
            Si no te registraste, ignorá este mensaje: no se creó ninguna cuenta.
        </p>
    </div>
    """

    mensaje = Message(
        subject=f"Confirmá tu correo — {marca.NOMBRE_PRODUCTO}",
        sender=remitente,
        recipients=[destinatario],
    )
    mensaje.html = cuerpo
    mensaje.body = (
        f"Hola {nombre}. Confirmá tu correo para activar tu cuenta:\n\n"
        f"{enlace}\n\nEl enlace vence en 48 horas."
    )
    return mensaje


def mail_bienvenida_paciente(destinatario, nombre, url_portal):
    remitente = _remitente()
    if not remitente or not destinatario:
        return None

    cuerpo = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color:#0f172a;">
        <h2 style="margin:0 0 16px;">Tu cuenta está lista</h2>
        <p style="font-size:15px; line-height:1.6; margin:0 0 24px;">
            Hola {nombre}. Desde ahora vas a poder ver en un solo lugar los estudios,
            recetas e informes que te envíen tus profesionales, sin importar en qué
            consultorio te atiendas.
        </p>
        <p style="margin:0 0 28px;">
            <a href="{url_portal}" style="{_ESTILO_BOTON}">Entrar a mi cuenta</a>
        </p>
        <p style="font-size:13px; color:#64748b; line-height:1.6; margin:0;">
            Si un profesional ya te había enviado algo antes de que te registraras,
            lo vas a encontrar ahí esperándote.
        </p>
    </div>
    """

    mensaje = Message(
        subject=f"Tu cuenta de {marca.NOMBRE_PRODUCTO} está lista",
        sender=remitente,
        recipients=[destinatario],
    )
    mensaje.html = cuerpo
    mensaje.body = (
        f"Hola {nombre}. Tu cuenta ya esta activa.\n\n{url_portal}\n\n"
        "Ahi vas a ver los estudios y recetas que te envien tus profesionales."
    )
    return mensaje


def mail_documento_enviado(destinatario, nombre_paciente, consultorio, tipo,
                           titulo, url_portal):
    """Le avisa al paciente que le llego algo nuevo.

    No adjunta el archivo: va al portal a buscarlo. Un estudio clinico en un
    correo viaja sin cifrar y queda en la bandeja de quien sea que lo reenvie.
    """
    remitente = _remitente()
    if not remitente or not destinatario:
        return None

    cuerpo = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color:#0f172a;">
        <h2 style="margin:0 0 16px;">Tenés un {tipo} nuevo</h2>
        <p style="font-size:15px; line-height:1.6; margin:0 0 8px;">
            Hola {nombre_paciente}. <strong>{consultorio}</strong> te envió:
        </p>
        <p style="font-size:15px; line-height:1.6; margin:0 0 24px;">
            <strong>{titulo}</strong>
        </p>
        <p style="margin:0 0 28px;">
            <a href="{url_portal}" style="{_ESTILO_BOTON}">Verlo en mi cuenta</a>
        </p>
        <p style="font-size:13px; color:#64748b; line-height:1.6; margin:0;">
            Por tu seguridad el documento no viaja en este correo: está guardado en
            tu cuenta.
        </p>
    </div>
    """

    mensaje = Message(
        subject=f"{consultorio} te envió un {tipo}",
        sender=remitente,
        recipients=[destinatario],
    )
    mensaje.html = cuerpo
    mensaje.body = (
        f"Hola {nombre_paciente}. {consultorio} te envio: {titulo}\n\n"
        f"Entra a verlo: {url_portal}\n\n"
        "Por tu seguridad el documento no viaja en este correo."
    )
    return mensaje
