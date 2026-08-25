"""Tests de pacientes, centrados en el manejo de la conexion.

De las 10 rutas del blueprint, 9 no cerraban la conexion ante una excepcion:
cada error dejaba una conexion ocupada en MySQL hasta que vencia wait_timeout.
Estos tests fijan que el context manager db_cursor la cierre siempre, incluidos
los caminos de salida temprana (404, duplicado), que es donde se escapaban.
"""

import mysql.connector
import pytest

from app.routes import pacientes_routes
from conftest import MockUser, login_as, make_db


def _director(client):
    login_as(client, MockUser(user_id=1, rol="director"))


# ------------------------------------------------------------- alta


def test_alta_rechaza_dni_duplicado_y_cierra_la_conexion(client, monkeypatch):
    _director(client)
    # La primera query (chequeo de duplicado) devuelve una fila -> hay duplicado.
    conexion, cursor = make_db(monkeypatch, pacientes_routes, fetchone_results=[{"id": 7}])

    respuesta = client.post("/api/pacientes", json={"dni": "12345678", "nombre": "Ana"})

    assert respuesta.status_code == 400
    assert "12345678" in respuesta.get_json()["error"]
    # No se llego al INSERT
    assert len(cursor.executed) == 1
    assert conexion.committed is False
    assert conexion.closed is True


def test_alta_exitosa_hace_commit_y_cierra(client, monkeypatch):
    _director(client)
    conexion, cursor = make_db(monkeypatch, pacientes_routes, fetchone_results=[None])

    respuesta = client.post(
        "/api/pacientes",
        json={"dni": "12345678", "nombre": "ana", "apellido": "perez"},
    )

    assert respuesta.status_code == 200
    assert conexion.committed is True
    assert conexion.closed is True
    # El apellido y el nombre se normalizan a mayusculas
    _, params = cursor.executed[1]
    assert "ANA" in params and "PEREZ" in params


def test_alta_cierra_la_conexion_si_falla_el_insert(client, monkeypatch):
    _director(client)
    conexion, _ = make_db(
        monkeypatch,
        pacientes_routes,
        fetchone_results=[None],
        execute_side_effects=[None, mysql.connector.Error("insert fallido")],
    )

    with pytest.raises(mysql.connector.Error):
        client.post("/api/pacientes", json={"dni": "1", "nombre": "x"})

    assert conexion.closed is True


# ------------------------------------------------------------- lectura


def test_get_paciente_inexistente_devuelve_404_y_cierra(client, monkeypatch):
    _director(client)
    conexion, _ = make_db(monkeypatch, pacientes_routes, fetchone_results=[None])

    respuesta = client.get("/api/pacientes/999")

    assert respuesta.status_code == 404
    assert conexion.closed is True


def test_listar_pacientes_devuelve_500_sin_filtrar_la_conexion(client, monkeypatch):
    """El handler captura la excepcion; la conexion tiene que cerrarse igual."""
    _director(client)
    conexion, _ = make_db(
        monkeypatch,
        pacientes_routes,
        execute_side_effects=[mysql.connector.Error("boom")],
    )

    respuesta = client.get("/api/pacientes")

    assert respuesta.status_code == 500
    assert conexion.closed is True


def test_listar_pacientes_no_expone_datos_clinicos_en_el_error(client, monkeypatch):
    _director(client)
    make_db(
        monkeypatch,
        pacientes_routes,
        execute_side_effects=[mysql.connector.Error("boom")],
    )

    cuerpo = client.get("/api/pacientes").get_data(as_text=True).lower()

    for termino in ("diagnostico", "antecedentes", "enfermedad_actual"):
        assert termino not in cuerpo


# ------------------------------------------------------------- borrado


def test_borrar_paciente_inexistente_devuelve_404_y_cierra(client, monkeypatch):
    _director(client)
    conexion, cursor = make_db(monkeypatch, pacientes_routes, fetchone_results=[None])

    respuesta = client.delete("/api/pacientes/999")

    assert respuesta.status_code == 404
    # No se llego al DELETE
    assert len(cursor.executed) == 1
    assert conexion.committed is False
    assert conexion.closed is True


def test_borrar_paciente_existente_hace_commit(client, monkeypatch):
    _director(client)
    conexion, cursor = make_db(monkeypatch, pacientes_routes, fetchone_results=[{"id": 5}])

    respuesta = client.delete("/api/pacientes/5")

    assert respuesta.status_code == 200
    assert any("DELETE FROM pacientes" in q for q in cursor.queries)
    assert conexion.committed is True
    assert conexion.closed is True


# ------------------------------------------------------------- busqueda


def test_buscar_pacientes_pagina_y_cierra(client, monkeypatch):
    _director(client)
    conexion, cursor = make_db(
        monkeypatch,
        pacientes_routes,
        fetchone_results=[{"total": 25}],
        fetchall_results=[[{"id": 1, "nro_hc": "1", "dni": "1", "nombre": "A", "apellido": "B"}]],
    )

    respuesta = client.get("/api/pacientes/buscar?q=per&page=2")
    datos = respuesta.get_json()

    assert respuesta.status_code == 200
    assert datos["total"] == 25
    assert datos["page"] == 2
    assert datos["total_pages"] == 3  # 25 / 10 -> 3 paginas
    # El offset de la pagina 2 es 10
    _, params = cursor.executed[1]
    assert params[-2:] == (10, 10)
    assert conexion.closed is True


def test_buscar_pacientes_requiere_login(client):
    assert client.get("/api/pacientes/buscar?q=x").status_code == 401


# ------------------------------------------------------------- nro de H.C.


def test_proximo_nro_hc_sugiere_el_siguiente(client, monkeypatch):
    _director(client)
    make_db(monkeypatch, pacientes_routes, fetchone_results=[{"max_hc": 1042}])

    respuesta = client.get("/api/pacientes/proximo-nro-hc")

    assert respuesta.status_code == 200
    assert respuesta.get_json()["proximo_nro_hc"] == "1043"


def test_proximo_nro_hc_arranca_en_uno_sin_pacientes(client, monkeypatch):
    _director(client)
    make_db(monkeypatch, pacientes_routes, fetchone_results=[{"max_hc": None}])

    assert client.get("/api/pacientes/proximo-nro-hc").get_json()["proximo_nro_hc"] == "1"


def test_proximo_nro_hc_ignora_los_no_numericos(client, monkeypatch):
    """La columna es VARCHAR: un CAST sobre 'HC-2024-A' daría 0 y sugeriría un número ya usado."""
    _director(client)
    _, cursor = make_db(monkeypatch, pacientes_routes, fetchone_results=[{"max_hc": 7}])

    client.get("/api/pacientes/proximo-nro-hc")

    assert any("REGEXP '^[0-9]+$'" in q for q in cursor.queries)


def test_proximo_nro_hc_requiere_login(client):
    assert client.get("/api/pacientes/proximo-nro-hc").status_code == 401
