"""Mail de aviso de comunicados importantes.

Se prueba el armado del mensaje, no el envio: el envio real vive en
utils/correo.py, que ya manda en segundo plano y traga sus propios errores.
"""

from app import app as flask_app
from app.utils.mails_comunicados import _cuerpo_html, enviar_aviso_comunicado


def test_el_titulo_y_el_contenido_van_escapados():
    """Los escribe una persona en un textarea. Sin escapar, un `<` suelto rompe
    el HTML del mail y cualquier etiqueta se interpreta en el cliente."""
    html = _cuerpo_html(
        "Cierre <urgente>",
        "Usar <script>alert(1)</script> no debe ejecutarse",
        "Ana & Cia",
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;urgente&gt;" in html
    assert "Ana &amp; Cia" in html


def test_sin_destinatarios_no_arma_mensaje(monkeypatch):
    """Publicar un importante cuando no hay a quien avisarle no es un error."""
    enviados = []
    monkeypatch.setattr(
        "app.utils.mails_comunicados.enviar_en_segundo_plano",
        lambda mensaje: enviados.append(mensaje),
    )

    with flask_app.app_context():
        assert enviar_aviso_comunicado([], "T", "C", "Autor") is None
        # Una lista de vacios equivale a no tener destinatarios.
        assert enviar_aviso_comunicado([None, ""], "T", "C", "Autor") is None

    assert enviados == []


def test_los_destinatarios_van_en_bcc(monkeypatch):
    """En To quedarian expuestos: son todos los usuarios del sistema, y cada
    persona que reciba el aviso veria la lista de mails del equipo."""
    enviados = []
    monkeypatch.setattr(
        "app.utils.mails_comunicados.enviar_en_segundo_plano",
        lambda mensaje: enviados.append(mensaje),
    )
    monkeypatch.setitem(flask_app.config, "MAIL_DEFAULT_SENDER", "cau@unsam.test")

    with flask_app.app_context():
        enviar_aviso_comunicado(["uno@cau.test", "dos@cau.test"], "Cierre", "C", "Autor")

    mensaje = enviados[0]
    assert mensaje.bcc == ["uno@cau.test", "dos@cau.test"]
    # En To va solo el remitente, nunca una direccion del equipo.
    assert mensaje.recipients == ["cau@unsam.test"]
    assert mensaje.subject == "[CAU UNSAM] Cierre"


def test_sin_remitente_configurado_no_se_manda(monkeypatch):
    """Antes caia al primer destinatario para tener un To valido, y esa
    direccion quedaba a la vista de todos los demas."""
    enviados = []
    monkeypatch.setattr(
        "app.utils.mails_comunicados.enviar_en_segundo_plano",
        lambda mensaje: enviados.append(mensaje),
    )
    monkeypatch.setitem(flask_app.config, "MAIL_DEFAULT_SENDER", None)

    with flask_app.app_context():
        resultado = enviar_aviso_comunicado(["uno@cau.test"], "T", "C", "Autor")

    assert resultado is None
    assert enviados == []
