"""Regresion: los usuarios dados de baja no deben poder autenticarse.

Los usuarios se borran con soft-delete (columna `activo`), nunca se eliminan de
la tabla. Cuando la carga del usuario no filtraba por activo = 1, dar de baja a
alguien no le impedia loguearse ni cerraba su sesion en curso: la cookie seguia
resolviendo a un usuario valido.

Estos tests miran la query, porque es donde vive el fix.
"""

import mysql.connector
import pytest

import app as app_module
from app import auth as auth_module
from conftest import FakeConnection, FakeCursor, patch_db_cursor

FILA_USUARIO = {
    "id": 1,
    "nombre": "Alice",
    "username": "alice",
    "email": "alice@example.com",
    "password_hash": "hash",
    "rol": "director",
    "duracion_turno": 30,
    "foto": None,
    "apellido": "Ejemplo",
    "dni": "12345678",
    "sexo": "F",
    "profesion": "Medica",
    "matricula_tipo": "MN",
    "matricula_numero": "1234",
    "matricula_provincia": "Buenos Aires",
}


def _enganchar(monkeypatch, modulo, cursor):
    """Los dos caminos de login pasan por db_cursor(), no por get_connection().

    Antes cerraban la conexion con un try/finally propio que dejaba el cursor
    abierto; ahora usan el context manager, y el doble tiene que engancharse
    ahi para que el test siga mirando lo mismo.
    """
    conexion = FakeConnection(cursor)
    patch_db_cursor(monkeypatch, modulo, conexion)
    return conexion


def test_obtener_por_username_filtra_por_activo(monkeypatch):
    cursor = FakeCursor(fetchone_results=[FILA_USUARIO])
    _enganchar(monkeypatch, auth_module, cursor)

    auth_module.Usuario.obtener_por_username("alice")

    query, params = cursor.executed[0]
    assert "activo = 1" in query.replace("  ", " ")
    assert params == ("alice",)


def test_load_user_filtra_por_activo(monkeypatch):
    cursor = FakeCursor(fetchone_results=[FILA_USUARIO])
    _enganchar(monkeypatch, app_module, cursor)

    app_module.load_user("1")

    query, params = cursor.executed[0]
    assert "activo = 1" in query.replace("  ", " ")
    assert params == ("1",)


def test_usuario_inactivo_no_se_resuelve(monkeypatch):
    """Si la fila no vuelve (porque el WHERE la excluye), no hay usuario."""
    cursor = FakeCursor(fetchone_results=[None])
    _enganchar(monkeypatch, app_module, cursor)

    assert app_module.load_user("1") is None


@pytest.mark.parametrize(
    "modulo, llamada",
    [
        (auth_module, lambda m: m.Usuario.obtener_por_username("alice")),
        (app_module, lambda m: m.load_user("1")),
    ],
)
def test_la_conexion_se_cierra_aunque_la_query_falle(monkeypatch, modulo, llamada):
    """El camino de login no debe filtrar conexiones ante un error de MySQL."""
    cursor = FakeCursor(
        execute_side_effects=[mysql.connector.Error("caida de la base")]
    )
    conexion = _enganchar(monkeypatch, modulo, cursor)

    with pytest.raises(mysql.connector.Error):
        llamada(modulo)

    assert conexion.closed is True
