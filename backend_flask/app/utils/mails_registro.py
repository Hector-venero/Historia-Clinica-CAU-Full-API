"""Correos del alta autoservicio: verificacion y bienvenida.

Siguen el patron del resto (`mails_turnos`, `mails_comunicados`): arman el
Message y lo devuelven, y quien llama decide como mandarlo. Devuelven None si no
hay remitente configurado, en lugar de fallar: no poder mandar un correo no tiene
que romper el alta.
"""

from flask import current_app
from flask_mail import Message


def _remitente():
    return current_app.config.get("MAIL_DEFAULT_SENDER")


def _url_base():
    """El dominio raiz de la plataforma, donde vive el sitio publico."""
    return (current_app.config.get("FRONTEND_URL") or "http://localhost:5173").rstrip("/")


_ESTILO_BOTON = (
    "display:inline-block;background:#059669;color:#ffffff;text-decoration:none;"
    "padding:14px 28px;border-radius:10px;font-weight:600;font-size:16px;"
)


def mail_verificacion(destinatario, nombre, token):
    remitente = _remitente()
    if not remitente or not destinatario:
        return None

    enlace = f"{_url_base()}/verificar/{token}"

    cuerpo = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color:#0f172a;">
        <h2 style="margin:0 0 16px;">Confirmá tu correo</h2>
        <p style="font-size:15px; line-height:1.6; margin:0 0 8px;">
            Estás a un paso de tener el sistema de <strong>{nombre}</strong> funcionando.
        </p>
        <p style="font-size:15px; line-height:1.6; margin:0 0 24px;">
            Hacé clic en el botón y creamos tu consultorio. Tarda unos segundos.
        </p>
        <p style="margin:0 0 28px;">
            <a href="{enlace}" style="{_ESTILO_BOTON}">Crear mi consultorio</a>
        </p>
        <p style="font-size:13px; color:#64748b; line-height:1.6; margin:0;">
            El enlace vence en 48 horas.<br>
            Si no te registraste, ignorá este mensaje: no se creó nada.
        </p>
    </div>
    """

    mensaje = Message(
        subject="Confirmá tu correo para activar tu consultorio",
        sender=remitente,
        recipients=[destinatario],
    )
    mensaje.html = cuerpo
    mensaje.body = (
        f"Confirmá tu correo para crear el sistema de {nombre}.\n\n"
        f"{enlace}\n\nEl enlace vence en 48 horas."
    )
    return mensaje


def mail_bienvenida(destinatario, nombre, url):
    remitente = _remitente()
    if not remitente or not destinatario:
        return None

    cuerpo = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color:#0f172a;">
        <h2 style="margin:0 0 16px;">Tu consultorio está listo</h2>
        <p style="font-size:15px; line-height:1.6; margin:0 0 24px;">
            El sistema de <strong>{nombre}</strong> ya está funcionando en tu propia dirección.
        </p>
        <p style="margin:0 0 28px;">
            <a href="{url}" style="{_ESTILO_BOTON}">Entrar a mi consultorio</a>
        </p>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:16px; margin:0 0 24px;">
            <p style="font-size:14px; line-height:1.6; margin:0; color:#334155;">
                <strong>Dirección:</strong> {url}<br>
                <strong>Usuario:</strong> admin<br>
                <strong>Contraseña:</strong> la que elegiste al registrarte
            </p>
        </div>
        <p style="font-size:13px; color:#64748b; line-height:1.6; margin:0;">
            Tenés 30 días de prueba. Te avisamos antes de que terminen.
        </p>
    </div>
    """

    mensaje = Message(
        subject=f"{nombre}: tu consultorio ya está listo",
        sender=remitente,
        recipients=[destinatario],
    )
    mensaje.html = cuerpo
    mensaje.body = (
        f"Tu consultorio ya está funcionando.\n\n"
        f"Dirección: {url}\nUsuario: admin\n"
        f"Contraseña: la que elegiste al registrarte\n\n"
        f"Tenés 30 días de prueba."
    )
    return mensaje
