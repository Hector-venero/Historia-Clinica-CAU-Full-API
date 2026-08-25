"""Comunicados internos: quien lee y quien publica.

Los lee cualquier usuario autenticado; publicar y borrar queda restringido a
director y administrativo.
"""

import pytest

from app.routes import comunicados_routes
from conftest import MockUser, login_as, make_db

COMUNICADO = {
    "id": 1,
    "titulo": "Cambio de horario",
    "contenido": "A partir del lunes...",
    "autor_id": 1,
    "creado_en": "2026-08-24 10:00:00",
    "actualizado_en": "2026-08-24 10:00:00",
    "autor_nombre": "Admin",
    "autor_rol": "director",
}


def _login(client, rol):
    login_as(client, MockUser(user_id=1, rol=rol))


# ---------------------------------------------------------------- lectura


@pytest.mark.parametrize("rol", ["director", "profesional", "administrativo", "area"])
def test_todos_los_roles_pueden_leer(client, monkeypatch, rol):
    _login(client, rol)
    make_db(monkeypatch, comunicados_routes, fetchall_results=[[dict(COMUNICADO)]])

    respuesta = client.get("/api/comunicados")

    assert respuesta.status_code == 200
    assert respuesta.get_json()[0]["titulo"] == "Cambio de horario"


@pytest.mark.parametrize(
    "rol, esperado",
    [("director", True), ("administrativo", True), ("profesional", False), ("area", False)],
)
def test_puede_eliminar_refleja_el_rol(client, monkeypatch, rol, esperado):
    """Es un dato para la UI; el permiso real lo aplica @requiere_rol en el DELETE."""
    _login(client, rol)
    make_db(monkeypatch, comunicados_routes, fetchall_results=[[dict(COMUNICADO)]])

    datos = client.get("/api/comunicados").get_json()

    assert datos[0]["puede_eliminar"] is esperado


def test_listar_requiere_login(client):
    assert client.get("/api/comunicados").status_code == 401


# ---------------------------------------------------------------- publicar


@pytest.mark.parametrize("rol", ["director", "administrativo"])
def test_los_publicadores_pueden_crear(client, monkeypatch, rol):
    _login(client, rol)
    conexion, cursor = make_db(monkeypatch, comunicados_routes)

    respuesta = client.post(
        "/api/comunicados", json={"titulo": "Aviso", "contenido": "Texto"}
    )

    assert respuesta.status_code == 201
    assert any("INSERT INTO comunicados" in q for q in cursor.queries)
    assert conexion.committed is True


@pytest.mark.parametrize("rol", ["profesional", "area"])
def test_los_demas_roles_no_pueden_crear(client, monkeypatch, rol):
    _login(client, rol)
    _, cursor = make_db(monkeypatch, comunicados_routes)

    respuesta = client.post(
        "/api/comunicados", json={"titulo": "Aviso", "contenido": "Texto"}
    )

    assert respuesta.status_code == 403
    assert not any("INSERT" in q for q in cursor.queries)


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"titulo": "", "contenido": "Texto"},
        {"titulo": "Aviso", "contenido": ""},
        {"titulo": "   ", "contenido": "   "},
        {},
    ],
)
def test_rechaza_titulo_o_contenido_vacios(client, monkeypatch, cuerpo):
    _login(client, "director")
    _, cursor = make_db(monkeypatch, comunicados_routes)

    respuesta = client.post("/api/comunicados", json=cuerpo)

    assert respuesta.status_code == 400
    assert not any("INSERT" in q for q in cursor.queries)


def test_el_autor_es_el_usuario_logueado(client, monkeypatch):
    login_as(client, MockUser(user_id=42, rol="director"))
    _, cursor = make_db(monkeypatch, comunicados_routes)

    client.post("/api/comunicados", json={"titulo": "Aviso", "contenido": "Texto"})

    insert = next(e for e in cursor.executed if "INSERT INTO comunicados" in e[0])
    assert insert[1][2] == 42


# ---------------------------------------------------------------- borrar


def test_eliminar_comunicado_existente(client, monkeypatch):
    _login(client, "director")
    conexion, cursor = make_db(monkeypatch, comunicados_routes, fetchone_results=[{"id": 3}])

    respuesta = client.delete("/api/comunicados/3")

    assert respuesta.status_code == 200
    assert any("DELETE FROM comunicados" in q for q in cursor.queries)
    assert conexion.committed is True


def test_eliminar_inexistente_devuelve_404_y_cierra(client, monkeypatch):
    _login(client, "director")
    conexion, cursor = make_db(monkeypatch, comunicados_routes, fetchone_results=[None])

    respuesta = client.delete("/api/comunicados/999")

    assert respuesta.status_code == 404
    assert not any("DELETE" in q for q in cursor.queries)
    assert conexion.closed is True


def test_un_profesional_no_puede_eliminar(client, monkeypatch):
    _login(client, "profesional")
    _, cursor = make_db(monkeypatch, comunicados_routes, fetchone_results=[{"id": 3}])

    assert client.delete("/api/comunicados/3").status_code == 403
    assert not any("DELETE" in q for q in cursor.queries)
