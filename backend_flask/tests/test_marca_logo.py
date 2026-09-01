"""El logo que va en un PDF: el del consultorio, o ninguno.

Los dos generadores de PDF tenian escrita a mano la ruta del escudo de la UNSAM,
asi que cualquier consultorio de la plataforma emitia historias clinicas con la
identidad de otra institucion. No es un detalle estetico: es un documento clinico
firmado con un logo ajeno.
"""

import os

from app import app as flask_app
from app import marca


class _ClienteFalso:
    def __init__(self, config=None):
        self.id = 1
        self.slug = "drlopez"
        self.nombre = "Consultorio Dr. Lopez"
        self.config = config or {}


def _con_cliente(monkeypatch, cliente):
    monkeypatch.setattr(marca, "_cliente", lambda: cliente)
    monkeypatch.setattr(marca, "_config", lambda: cliente.config if cliente else None)


def test_un_consultorio_sin_logo_no_recibe_ninguno(monkeypatch):
    """Es el fallo que motivo el cambio: caia al escudo del CAU."""
    _con_cliente(monkeypatch, _ClienteFalso())

    with flask_app.app_context():
        assert marca.logo_archivo() is None


def test_un_logo_configurado_que_no_esta_en_disco_tampoco_cae_a_otro(monkeypatch):
    """Mejor el nombre en texto que el logo de otra institucion."""
    _con_cliente(monkeypatch, _ClienteFalso({"logo": "no_existe.png"}))

    with flask_app.app_context():
        assert marca.logo_archivo() is None


def test_la_instalacion_de_un_solo_centro_conserva_su_logo(monkeypatch):
    """En `main` vive el CAU, y ahi ese escudo es el que corresponde.

    Sin esta rama, arreglar la plataforma le sacaba el logo a los PDF del CAU.
    """
    _con_cliente(monkeypatch, None)
    monkeypatch.delenv("MARCA_LOGO", raising=False)

    with flask_app.app_context():
        ruta = marca.logo_archivo()
        existe = os.path.exists(
            os.path.join(flask_app.root_path, "static", "img", marca.LOGO_INSTALACION)
        )
        assert (ruta is not None) == existe


def test_el_logo_propio_se_resuelve_dentro_de_static(monkeypatch):
    """Llega como URL o como nombre suelto; al PDF solo le sirve el archivo."""
    _con_cliente(monkeypatch, _ClienteFalso({"logo": "/static/marcas/drlopez.png"}))

    with flask_app.app_context():
        carpeta = os.path.join(flask_app.root_path, "static", "marcas")
        os.makedirs(carpeta, exist_ok=True)
        destino = os.path.join(carpeta, "drlopez.png")
        creado = not os.path.exists(destino)
        if creado:
            open(destino, "wb").close()
        try:
            assert marca.logo_archivo() == destino
        finally:
            if creado:
                os.remove(destino)
