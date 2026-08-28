"""Mail de aviso de un comunicado importante.

Solo se manda para los comunicados marcados como `importante`. Los normales
viven en la campana de la barra superior y nada mas: si cada aviso generara un
mail, la casilla se vuelve ruido y el equipo deja de abrirlos, que es
exactamente lo que no se quiere cuando de verdad hay algo urgente.

El cuerpo repite el texto completo del comunicado en vez de mandar solo un link.
La mayoria son de pocas lineas, y obligar a entrar al sistema para leer dos
frases agrega una friccion que hace que no se lean.
"""

from html import escape

from flask import current_app
from flask_mail import Message

from app import marca
from app.utils.correo import enviar_en_segundo_plano

def _pie():
    return f"""
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
    <p style="font-size: 13px; color: #94a3b8; text-align: center; margin: 0;">
        Recibis este aviso porque forma parte de los comunicados internos del
        {marca.nombre_corto()}.<br>Es un mensaje automatico, no responder.
    </p>
"""


def _cuerpo_html(titulo, contenido, autor):
    # escape() en los tres: el titulo y el contenido los escribe una persona en
    # un textarea, asi que un < suelto romperia el HTML del mail y cualquier
    # etiqueta se interpretaria en el cliente de correo.
    return f"""
    <div style="font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
        <p style="display: inline-block; background: #fef3c7; color: #92400e; font-size: 12px;
                  font-weight: 700; letter-spacing: 0.05em; padding: 4px 10px; border-radius: 4px; margin: 0 0 16px;">
            COMUNICADO IMPORTANTE
        </p>
        <h1 style="font-size: 22px; color: #0f172a; margin: 0 0 16px;">{escape(titulo)}</h1>
        <div style="font-size: 15px; color: #334155; line-height: 1.7; white-space: pre-wrap;">{escape(contenido)}</div>
        <p style="font-size: 14px; color: #64748b; margin-top: 24px;">Publicado por {escape(autor)}.</p>
        {_pie()}
    </div>
    """


def enviar_aviso_comunicado(destinatarios, titulo, contenido, autor):
    """Avisa por mail de un comunicado importante.

    Los destinatarios van en Bcc y no en To: son todos los usuarios activos del
    sistema, y ponerlos en To expondria la lista de mails del equipo a cada
    persona que reciba el aviso.

    Devuelve el hilo de envio, o None si no hay a quien mandarle.
    """
    destinatarios = [correo for correo in destinatarios if correo]
    if not destinatarios:
        return None

    remitente = current_app.config.get("MAIL_DEFAULT_SENDER")
    if not remitente:
        # Sin remitente no se manda. La alternativa era poner al primer
        # destinatario en To para que el servidor acepte el mensaje, y eso
        # expone su direccion al resto: justo lo que el Bcc evita. Si el correo
        # no esta configurado, el comunicado igual queda publicado y visible en
        # la campana.
        current_app.logger.warning(
            "MAIL_DEFAULT_SENDER sin configurar: no se envia el aviso de '%s'", titulo
        )
        return None

    mensaje = Message(
        subject=f"[{marca.nombre_corto()}] {titulo}",
        sender=remitente,
        # El servidor necesita al menos un destinatario visible para aceptar el
        # mensaje, asi que el remitente se lo manda a si mismo y el equipo va
        # entero en Bcc.
        recipients=[remitente],
        bcc=destinatarios,
        html=_cuerpo_html(titulo, contenido, autor),
    )

    return enviar_en_segundo_plano(mensaje)
