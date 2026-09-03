"""Subir el logo del consultorio.

Es la pieza que faltaba para que un consultorio deje de emitir historias
clinicas con el nombre en texto —o, antes, con el escudo de otra institucion—.
Lo que se prueba aca es quien puede hacerlo y que se acepta.
"""

import io as _io

from app.routes import marca_routes as mr
from conftest import MockUser, login_as


class _ClienteFalso:
    id = 1
    slug = "drlopez"
    nombre = "Consultorio Dr. Lopez"
    config = {}


def _png_minimo():
    """Un PNG de verdad, chico. Que sea valido importa: el endpoint mira la
    extension, pero el PDF despues tiene que poder dibujarlo."""
    import struct, zlib

    def trozo(tipo, datos):
        cuerpo = tipo + datos
        return struct.pack(">I", len(datos)) + cuerpo + struct.pack(">I", zlib.crc32(cuerpo) & 0xFFFFFFFF)

    crudo = b"".join(b"\x00" + bytes([0, 120, 90] * 8) for _ in range(8))
    return (
        b"\x89PNG\r\n\x1a\n"
        + trozo(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
        + trozo(b"IDAT", zlib.compress(crudo))
        + trozo(b"IEND", b"")
    )


def _subir(client, nombre="logo.png", contenido=None):
    return client.post(
        "/api/marca/logo",
        data={"logo": (_io.BytesIO(contenido or _png_minimo()), nombre)},
        content_type="multipart/form-data",
    )


def test_un_administrativo_no_puede_cambiar_el_logo(client, monkeypatch):
    """Es la identidad del consultorio, no algo del uso diario."""
    monkeypatch.setattr(mr, "cliente_actual", lambda: _ClienteFalso())
    login_as(client, MockUser(1, "administrativo"))

    assert _subir(client).status_code == 403


def test_un_profesional_tampoco(client, monkeypatch):
    monkeypatch.setattr(mr, "cliente_actual", lambda: _ClienteFalso())
    login_as(client, MockUser(1, "profesional"))

    assert _subir(client).status_code == 403


def test_un_formato_que_el_pdf_no_dibuja_se_rechaza(client, monkeypatch):
    """SVG queda afuera a proposito: se ve en pantalla pero no en el PDF, y un
    logo a medias es peor que ninguno."""
    monkeypatch.setattr(mr, "cliente_actual", lambda: _ClienteFalso())
    login_as(client, MockUser(1, "director"))

    respuesta = _subir(client, nombre="logo.svg", contenido=b"<svg/>")

    assert respuesta.status_code == 400
    assert "PNG" in respuesta.get_json()["error"]


def test_sin_archivo_no_rompe(client, monkeypatch):
    monkeypatch.setattr(mr, "cliente_actual", lambda: _ClienteFalso())
    login_as(client, MockUser(1, "director"))

    respuesta = client.post("/api/marca/logo", data={}, content_type="multipart/form-data")

    assert respuesta.status_code == 400


def test_en_la_instalacion_de_un_solo_centro_se_avisa(client, monkeypatch):
    """Ahi el logo viene del entorno: no hay plano de control donde guardarlo."""
    monkeypatch.setattr(mr, "cliente_actual", lambda: None)
    login_as(client, MockUser(1, "director"))

    respuesta = _subir(client)

    assert respuesta.status_code == 400
    assert "consultorio" in respuesta.get_json()["error"]


# --------------------------------------------------- la URL tiene que resolver


def test_la_url_del_logo_lleva_el_prefijo_api(client, monkeypatch, tmp_path):
    """⚠️ `/static/...` a secas NO llega al backend.

    Ni nginx ni el servidor de desarrollo lo enrutan a Flask: nginx solo manda
    `/api/` y Vite solo proxea `/api`. Una URL sin ese prefijo cae en el
    catch-all de la aplicacion y devuelve el index.html — **200 con text/html
    donde el navegador espera una imagen**. El logo se veia roto y parecia un
    problema de formato del archivo subido.
    """
    from app import marca

    assert marca.PREFIJO_ESTATICO == "/api"


def test_un_logo_viejo_se_normaliza_al_leerlo(monkeypatch):
    """Los subidos antes del arreglo quedaron como `/static/marcas/...`.

    Se corrige al leer y no con una migracion: asi el logo que alguien ya subio
    empieza a verse sin tener que volver a subirlo.
    """
    from app import marca

    assert marca._url_servible("/static/marcas/drlopez.jpeg") == "/api/static/marcas/drlopez.jpeg"


def test_no_se_agrega_el_prefijo_dos_veces(monkeypatch):
    """Guardado ya correcto, se deja como esta."""
    from app import marca

    ruta = "/api/static/marcas/drlopez.jpeg"
    assert marca._url_servible(ruta) == ruta


def test_una_url_externa_no_se_toca(monkeypatch):
    """MARCA_LOGO puede apuntar a un CDN en una instalacion propia."""
    from app import marca

    ruta = "https://ejemplo.com/logo.png"
    assert marca._url_servible(ruta) == ruta


def test_sin_logo_sigue_siendo_none(monkeypatch):
    from app import marca

    assert marca._url_servible(None) is None
