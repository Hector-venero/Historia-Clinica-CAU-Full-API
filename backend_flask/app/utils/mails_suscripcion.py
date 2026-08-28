"""Avisos del ciclo de la suscripcion: vencimiento proximo y suspension.

Mismo patron que el resto: arman el Message y lo devuelven; devuelven None si no
hay remitente configurado, para que no poder mandar un correo no rompa la tarea.
"""

from flask import current_app
from flask_mail import Message

_ESTILO_BOTON = (
    "display:inline-block;background:#059669;color:#ffffff;text-decoration:none;"
    "padding:14px 28px;border-radius:10px;font-weight:600;font-size:16px;"
)


def _remitente():
    return current_app.config.get("MAIL_DEFAULT_SENDER")


def _contacto():
    return current_app.config.get("MAIL_DEFAULT_SENDER") or "soporte"


def mail_aviso_vencimiento(destinatario, nombre, prueba_hasta):
    remitente = _remitente()
    if not remitente or not destinatario:
        return None

    fecha = prueba_hasta.strftime("%d/%m/%Y") if hasattr(prueba_hasta, "strftime") else prueba_hasta

    cuerpo = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color:#0f172a;">
        <h2 style="margin:0 0 16px;">Tu prueba termina el {fecha}</h2>
        <p style="font-size:15px; line-height:1.6; margin:0 0 16px;">
            El periodo de prueba de <strong>{nombre}</strong> esta por terminar.
        </p>
        <p style="font-size:15px; line-height:1.6; margin:0 0 16px;">
            Si querés seguir usándolo, escribinos a <strong>{_contacto()}</strong> y lo dejamos activo.
        </p>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:16px; margin:0 0 8px;">
            <p style="font-size:14px; line-height:1.6; margin:0; color:#334155;">
                <strong>Tus datos no se borran.</strong> Si la prueba vence, se corta el acceso
                al sistema pero las historias clínicas siguen guardadas, y vas a poder
                descargarlas cuando quieras.
            </p>
        </div>
    </div>
    """

    mensaje = Message(
        subject=f"{nombre}: tu prueba termina el {fecha}",
        sender=remitente,
        recipients=[destinatario],
    )
    mensaje.html = cuerpo
    mensaje.body = (
        f"El periodo de prueba de {nombre} termina el {fecha}.\n\n"
        f"Para seguir usandolo, escribinos a {_contacto()}.\n\n"
        "Tus datos no se borran: si vence, vas a poder descargarlos igual."
    )
    return mensaje


def mail_suspendido(destinatario, nombre):
    remitente = _remitente()
    if not remitente or not destinatario:
        return None

    cuerpo = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color:#0f172a;">
        <h2 style="margin:0 0 16px;">Se pausó el acceso a {nombre}</h2>
        <p style="font-size:15px; line-height:1.6; margin:0 0 16px;">
            Terminó el periodo de prueba, así que por ahora no se puede usar el sistema
            para trabajar.
        </p>
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px; padding:16px; margin:0 0 20px;">
            <p style="font-size:14px; line-height:1.6; margin:0; color:#166534;">
                <strong>Tus historias clínicas están intactas.</strong> Podés entrar al sistema
                y descargarlas todas cuando quieras: son datos de tus pacientes, no nuestros.
            </p>
        </div>
        <p style="font-size:15px; line-height:1.6; margin:0;">
            Para reactivarlo, escribinos a <strong>{_contacto()}</strong>.
        </p>
    </div>
    """

    mensaje = Message(
        subject=f"{nombre}: se pausó el acceso",
        sender=remitente,
        recipients=[destinatario],
    )
    mensaje.html = cuerpo
    mensaje.body = (
        f"Termino el periodo de prueba de {nombre} y se pauso el acceso.\n\n"
        "Tus historias clinicas estan intactas: podes entrar y descargarlas cuando "
        f"quieras.\n\nPara reactivarlo, escribinos a {_contacto()}."
    )
    return mensaje
