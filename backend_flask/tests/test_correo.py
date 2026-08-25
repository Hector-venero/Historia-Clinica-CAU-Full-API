"""El envio de correo no bloquea el request."""

import threading
import time

from flask_mail import Message

from app import app as flask_app
from app.utils import correo


def test_el_envio_no_bloquea(monkeypatch):
    """Un SMTP lento no debe demorar la respuesta de la API."""
    liberado = threading.Event()

    class MailLento:
        # flask_mail lo lee al construir el Message
        default_sender = "cau@test.local"

        def send(self, _mensaje):
            liberado.wait(timeout=5)

    monkeypatch.setitem(flask_app.extensions, "mail", MailLento())

    with flask_app.app_context():
        inicio = time.monotonic()
        hilo = correo.enviar_en_segundo_plano(
            Message(subject="x", recipients=["a@b.test"], body="y")
        )
        transcurrido = time.monotonic() - inicio

    # La llamada vuelve enseguida aunque el envio siga en curso.
    assert transcurrido < 0.5
    assert hilo.is_alive()
    liberado.set()
    hilo.join(timeout=5)


def test_un_fallo_del_smtp_no_propaga(monkeypatch):
    """La operacion que origino el aviso ya termino bien: no se puede romper."""
    class MailRoto:
        default_sender = "cau@test.local"

        def send(self, _mensaje):
            raise RuntimeError("smtp caido")

    monkeypatch.setitem(flask_app.extensions, "mail", MailRoto())

    with flask_app.app_context():
        hilo = correo.enviar_en_segundo_plano(
            Message(subject="x", recipients=["a@b.test"], body="y")
        )
    hilo.join(timeout=5)

    assert not hilo.is_alive()
