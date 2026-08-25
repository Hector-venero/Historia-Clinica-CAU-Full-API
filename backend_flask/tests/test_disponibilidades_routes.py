"""Disponibilidades: canonicalizacion de dias y validacion contra turnos.

El bug principal: normalizar_dia devolvia "Miercoles" y "Sabado" CON tilde,
pero el ENUM de la columna los tiene SIN tilde. Guardar disponibilidad para
esos dos dias fallaba con error 1265 "Data truncated" — verificado contra
MySQL 8.0. Estos tests fijan la forma canonica.
"""

from datetime import datetime, timedelta

import pytest

from app.routes import disponibilidades_routes as disp
from conftest import MockUser, login_as, make_db

# Valores exactos del ENUM en db/init.sql
VALORES_DEL_ENUM = {"Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"}


# ---------------------------------------------------- canonicalizacion


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("miércoles", "Miercoles"),
        ("Miércoles", "Miercoles"),
        ("miercoles", "Miercoles"),
        ("  MIÉRCOLES  ", "Miercoles"),
        ("sábado", "Sabado"),
        ("Sabado", "Sabado"),
        ("lunes", "Lunes"),
        ("domingo", "Domingo"),
    ],
)
def test_normalizar_dia_acepta_con_y_sin_tilde(entrada, esperado):
    assert disp.normalizar_dia(entrada) == esperado


def test_normalizar_dia_siempre_devuelve_un_valor_del_enum():
    """Si devolviera una tilde, el INSERT fallaría con 1265."""
    for dia in ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"):
        assert disp.normalizar_dia(dia) in VALORES_DEL_ENUM


def test_dias_ordenados_coincide_con_el_enum():
    """Se interpola en un FIELD() del ORDER BY: un valor ajeno rompe el orden."""
    assert set(disp.DIAS_ORDENADOS) == VALORES_DEL_ENUM


def test_normalizar_dia_rechaza_basura():
    assert disp.normalizar_dia("no-es-un-dia") is None
    assert disp.normalizar_dia("") is None
    assert disp.normalizar_dia(None) is None


def test_crear_disponibilidad_guarda_el_dia_canonico(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol="profesional"))
    _, cursor = make_db(monkeypatch, disp)

    respuesta = client.post(
        "/api/disponibilidades",
        json={"dia_semana": "Miércoles", "hora_inicio": "09:00", "hora_fin": "12:00"},
    )

    assert respuesta.status_code == 201
    insert = next(e for e in cursor.executed if "INSERT INTO disponibilidades" in e[0])
    assert "Miercoles" in insert[1]  # sin tilde


def test_crear_disponibilidad_rechaza_dia_invalido(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol="profesional"))
    _, cursor = make_db(monkeypatch, disp)

    respuesta = client.post(
        "/api/disponibilidades",
        json={"dia_semana": "Lunez", "hora_inicio": "09:00", "hora_fin": "12:00"},
    )

    assert respuesta.status_code == 400
    assert not any("INSERT" in q for q in cursor.queries)


# ---------------------------------------------------- permisos


def test_un_profesional_no_puede_crear_para_otro(client, monkeypatch):
    """El usuario_id del body se ignora: se fuerza el propio."""
    login_as(client, MockUser(user_id=7, rol="profesional"))
    _, cursor = make_db(monkeypatch, disp)

    client.post(
        "/api/disponibilidades",
        json={
            "usuario_id": 99,
            "dia_semana": "Lunes",
            "hora_inicio": "09:00",
            "hora_fin": "12:00",
        },
    )

    insert = next(e for e in cursor.executed if "INSERT INTO disponibilidades" in e[0])
    assert insert[1][0] == 7


def test_un_director_si_puede_crear_para_otro(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol="director"))
    _, cursor = make_db(monkeypatch, disp)

    client.post(
        "/api/disponibilidades",
        json={
            "usuario_id": 99,
            "dia_semana": "Lunes",
            "hora_inicio": "09:00",
            "hora_fin": "12:00",
        },
    )

    insert = next(e for e in cursor.executed if "INSERT INTO disponibilidades" in e[0])
    assert insert[1][0] == 99


def test_un_profesional_no_puede_editar_la_de_otro(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    make_db(monkeypatch, disp, fetchone_results=[{"usuario_id": 99}])

    respuesta = client.put(
        "/api/disponibilidades/5", json={"hora_inicio": "09:00", "hora_fin": "12:00"}
    )

    assert respuesta.status_code == 403


def test_disponibilidades_requiere_login(client):
    assert client.get("/api/disponibilidades").status_code == 401


# ---------------------------------------------------- validar


def _turno(dias_adelante, hora_inicio, hora_fin, nombre="Ana"):
    base = (datetime.now() + timedelta(days=dias_adelante)).replace(
        hour=int(hora_inicio[:2]), minute=int(hora_inicio[3:5]), second=0, microsecond=0
    )
    fin = base.replace(hour=int(hora_fin[:2]), minute=int(hora_fin[3:5]))
    return {
        "id": 1,
        "fecha_inicio": base,
        "fecha_fin": fin,
        "motivo": "control",
        "paciente": nombre,
    }


def _dia_es(dt):
    return disp.DIAS_EN_A_ES[dt.strftime("%A")]


def test_validar_detecta_turnos_que_quedarian_huerfanos(client, monkeypatch):
    """Achicar una franja no cancela los turnos ya dados: hay que avisar."""
    login_as(client, MockUser(user_id=1, rol="profesional"))
    turno = _turno(7, "16:00", "16:30")
    make_db(monkeypatch, disp, fetchall_results=[[turno]])

    # La franja propuesta termina a las 12: el turno de las 16 queda afuera.
    respuesta = client.post(
        "/api/disponibilidades/validar",
        json={
            "disponibilidades": [
                {
                    "dia_semana": _dia_es(turno["fecha_inicio"]),
                    "hora_inicio": "09:00",
                    "hora_fin": "12:00",
                    "activo": True,
                }
            ]
        },
    )

    fuera = respuesta.get_json()
    assert respuesta.status_code == 200
    assert len(fuera) == 1
    assert fuera[0]["paciente"] == "Ana"


def test_validar_no_reporta_los_turnos_cubiertos(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol="profesional"))
    turno = _turno(7, "10:00", "10:30")
    make_db(monkeypatch, disp, fetchall_results=[[turno]])

    respuesta = client.post(
        "/api/disponibilidades/validar",
        json={
            "disponibilidades": [
                {
                    "dia_semana": _dia_es(turno["fecha_inicio"]),
                    "hora_inicio": "09:00",
                    "hora_fin": "12:00",
                    "activo": True,
                }
            ]
        },
    )

    assert respuesta.get_json() == []


def test_validar_ignora_las_franjas_desactivadas(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol="profesional"))
    turno = _turno(7, "10:00", "10:30")
    make_db(monkeypatch, disp, fetchall_results=[[turno]])

    respuesta = client.post(
        "/api/disponibilidades/validar",
        json={
            "disponibilidades": [
                {
                    "dia_semana": _dia_es(turno["fecha_inicio"]),
                    "hora_inicio": "09:00",
                    "hora_fin": "12:00",
                    "activo": False,
                }
            ]
        },
    )

    # Con la franja apagada, ese turno queda sin cobertura.
    assert len(respuesta.get_json()) == 1


def test_validar_acepta_el_dia_con_tilde(client, monkeypatch):
    """El frontend puede mandar 'Miércoles'; se normaliza antes de comparar."""
    login_as(client, MockUser(user_id=1, rol="profesional"))
    # Buscar el próximo miércoles
    hoy = datetime.now()
    dias = (2 - hoy.weekday()) % 7 or 7
    turno = _turno(dias, "10:00", "10:30")
    assert _dia_es(turno["fecha_inicio"]) == "Miercoles"

    make_db(monkeypatch, disp, fetchall_results=[[turno]])

    respuesta = client.post(
        "/api/disponibilidades/validar",
        json={
            "disponibilidades": [
                {
                    "dia_semana": "Miércoles",
                    "hora_inicio": "09:00",
                    "hora_fin": "12:00",
                    "activo": True,
                }
            ]
        },
    )

    assert respuesta.get_json() == []


def test_validar_requiere_login(client):
    assert client.post("/api/disponibilidades/validar", json={}).status_code == 401
