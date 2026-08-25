"""Subida de foto de perfil.

Dos bugs que cubren estos tests:

- La carpeta de destino estaba hardcodeada a /app/static/fotos_usuarios, una
  ruta que solo existe dentro del contenedor: correr el backend fuera de Docker
  rompia la subida.

- Cuando Pillow no podia procesar la imagen, el except guardaba el stream
  crudo... pero Image.open() ya lo habia consumido. El archivo resultante
  quedaba en 0 bytes y la foto salia rota, sin ningun error visible.
"""

import io

import pytest
from PIL import Image

from app import app as flask_app
from app.routes import usuarios_routes
from conftest import MockUser, login_as, make_db


@pytest.fixture
def carpeta_fotos(tmp_path, monkeypatch):
    """Redirige las fotos a un temporal.

    La carpeta se deriva de app.root_path, asi que basta con moverlo: si el
    codigo volviera a hardcodear la ruta, estos tests escribirian en la carpeta
    real y el de los 0 bytes fallaria.
    """
    monkeypatch.setattr(flask_app, "root_path", str(tmp_path))
    destino = tmp_path / "static" / "fotos_usuarios"
    return destino


def _imagen_valida():
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color="red").save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer


def test_actualizar_perfil_sin_foto(client, monkeypatch, carpeta_fotos):
    login_as(client, MockUser(user_id=1, rol="profesional"))
    conexion, _ = make_db(monkeypatch, usuarios_routes)

    respuesta = client.post(
        "/api/usuario/perfil",
        data={"nombre": "Nuevo Nombre", "email": "nuevo@example.com"},
    )

    assert respuesta.status_code == 200
    assert conexion.committed is True
    assert conexion.closed is True


def test_guarda_la_foto_en_la_carpeta_derivada_del_root_path(client, monkeypatch, carpeta_fotos):
    """Si la ruta volviera a ser absoluta, no se escribiría acá."""
    login_as(client, MockUser(user_id=1, rol="profesional"))
    make_db(monkeypatch, usuarios_routes)

    respuesta = client.post(
        "/api/usuario/perfil",
        data={
            "nombre": "Nuevo Nombre",
            "email": "nuevo@example.com",
            "foto": (_imagen_valida(), "test.jpg"),
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["foto"] == "user_1.jpg"

    guardada = carpeta_fotos / "user_1.jpg"
    assert guardada.exists()
    assert guardada.stat().st_size > 0


def test_una_imagen_corrupta_no_produce_un_archivo_vacio(client, monkeypatch, carpeta_fotos):
    """El bug del seek(0): Image.open() consumía el stream y quedaba 0 bytes."""
    login_as(client, MockUser(user_id=1, rol="profesional"))
    make_db(monkeypatch, usuarios_routes)

    contenido = b"esto no es una imagen, Pillow va a fallar" * 10
    corrupta = io.BytesIO(contenido)

    respuesta = client.post(
        "/api/usuario/perfil",
        data={
            "nombre": "Nuevo Nombre",
            "email": "nuevo@example.com",
            "foto": (corrupta, "roto.jpg"),
        },
    )

    assert respuesta.status_code == 200

    guardada = carpeta_fotos / "user_1.jpg"
    assert guardada.exists()
    # Lo que importa: el archivo conserva todos sus bytes.
    assert guardada.stat().st_size == len(contenido)


def test_borrar_foto_sin_foto_cierra_la_conexion(client, monkeypatch, carpeta_fotos):
    """El return temprano dejaba la conexión abierta."""
    login_as(client, MockUser(user_id=1, rol="profesional"))
    conexion, _ = make_db(monkeypatch, usuarios_routes, fetchone_results=[{"foto": None}])

    respuesta = client.delete("/api/usuario/foto")

    assert respuesta.status_code == 200
    assert respuesta.get_json()["foto"] is None
    assert conexion.closed is True


def test_borrar_foto_elimina_el_archivo(client, monkeypatch, carpeta_fotos):
    login_as(client, MockUser(user_id=1, rol="profesional"))
    carpeta_fotos.mkdir(parents=True, exist_ok=True)
    archivo = carpeta_fotos / "user_1.jpg"
    archivo.write_bytes(b"contenido")

    conexion, _ = make_db(
        monkeypatch, usuarios_routes, fetchone_results=[{"foto": "user_1.jpg"}]
    )

    respuesta = client.delete("/api/usuario/foto")

    assert respuesta.status_code == 200
    assert not archivo.exists()
    assert conexion.committed is True


def test_actualizar_perfil_requiere_login(client):
    assert client.post("/api/usuario/perfil", data={}).status_code == 401
