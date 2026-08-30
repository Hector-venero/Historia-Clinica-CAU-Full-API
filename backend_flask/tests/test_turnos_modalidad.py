"""Videoconsulta: modalidad del turno y enlace de la videollamada.

El enlace no lo genera el sistema, lo pega el profesional con la herramienta que
ya usa. Por eso hay que validarlo **antes** de guardarlo: termina en el correo
del paciente y en su portal, y si esta mal el error se descubre a la hora del
turno, con el paciente esperando del otro lado.

Estos tests miran la validacion y lo que se escribe, que es donde vive la
decision. El envio del correo tiene sus propios dobles.
"""

import pytest

from app.routes import turnos_routes as tr
from conftest import MockUser, login_as, make_db

ENLACE = "https://meet.example.com/abc-defg-hij"


# ------------------------------------------------------- la validacion


def test_por_defecto_el_turno_es_presencial():
    """Todo lo que ya existia sigue entrando igual: sin `modalidad`, presencial."""
    modalidad, enlace, error = tr._leer_modalidad({})

    assert (modalidad, enlace, error) == ("presencial", None, None)


def test_una_modalidad_inventada_se_rechaza():
    _m, _e, error = tr._leer_modalidad({"modalidad": "telepatia"})

    assert error and "presencial" in error


def test_un_turno_virtual_sin_enlace_se_rechaza():
    """Un turno virtual sin enlace no le sirve a nadie: el paciente recibe un
    correo que le dice que no vaya al consultorio y no le dice adonde ir."""
    _m, _e, error = tr._leer_modalidad({"modalidad": "virtual"})

    assert error and "enlace" in error


@pytest.mark.parametrize(
    "enlace",
    [
        "http://meet.example.com/sala",  # sin cifrar
        "meet.example.com/sala",         # sin esquema
        "javascript:alert(1)",
        "   ",
    ],
)
def test_un_enlace_que_no_es_https_se_rechaza(enlace):
    """Una sala de videoconsulta servida por http es una consulta medica en
    claro, y un `javascript:` en un correo es otra cosa distinta y peor."""
    _m, _e, error = tr._leer_modalidad({"modalidad": "virtual", "enlace_video": enlace})

    assert error is not None


def test_un_enlace_valido_se_acepta_y_se_limpia():
    modalidad, enlace, error = tr._leer_modalidad(
        {"modalidad": "  VIRTUAL  ", "enlace_video": f"  {ENLACE}  "}
    )

    assert (modalidad, enlace, error) == ("virtual", ENLACE, None)


def test_un_enlace_en_un_turno_presencial_se_descarta():
    """Si no, queda un enlace muerto que despues aparece en el portal del
    paciente sobre un turno al que tiene que ir en persona."""
    modalidad, enlace, error = tr._leer_modalidad(
        {"modalidad": "presencial", "enlace_video": ENLACE}
    )

    assert (modalidad, enlace, error) == ("presencial", None, None)


def test_un_enlace_demasiado_largo_se_rechaza():
    """La columna es VARCHAR(500): cortarlo en silencio daria un enlace roto."""
    _m, _e, error = tr._leer_modalidad(
        {"modalidad": "virtual", "enlace_video": "https://x.com/" + "a" * 600}
    )

    assert error is not None


# ------------------------------------------------------- lo que se guarda


def _crear_turno(client, monkeypatch, payload):
    monkeypatch.setattr(tr, "medico_disponible", lambda *a, **kw: True)
    monkeypatch.setattr(tr, "enviar_confirmacion", lambda *a, **kw: True)
    monkeypatch.setattr(
        tr, "_alinear_turno_individual",
        lambda *a: (
            __import__("datetime").datetime(2026, 9, 7, 9, 0),
            __import__("datetime").datetime(2026, 9, 7, 9, 20),
            None,
            None,
        ),
    )
    _conn, cursor = make_db(
        monkeypatch, tr,
        fetchone_results=[{"id": 1, "email": "a@b.com", "nombre": "Ana", "apellido": "Diaz"},
                          {"nombre": "Dr. Lopez"}],
    )
    login_as(client, MockUser(1, "director"))
    respuesta = client.post("/api/turnos", json=payload)
    return respuesta, cursor


BASE = {"paciente_id": 1, "usuario_id": 1, "fecha_inicio": "2026-09-07T09:00:00"}


def test_el_turno_virtual_guarda_modalidad_y_enlace(client, monkeypatch):
    respuesta, cursor = _crear_turno(
        client, monkeypatch, {**BASE, "modalidad": "virtual", "enlace_video": ENLACE}
    )

    assert respuesta.status_code == 201
    insert = next(q for q in cursor.executed if "INSERT INTO turnos" in q[0])
    assert "modalidad" in insert[0] and "enlace_video" in insert[0]
    assert "virtual" in insert[1] and ENLACE in insert[1]


def test_el_turno_presencial_sigue_entrando_como_siempre(client, monkeypatch):
    """La regresion que importa: lo que ya funcionaba no puede cambiar."""
    respuesta, cursor = _crear_turno(client, monkeypatch, BASE)

    assert respuesta.status_code == 201
    insert = next(q for q in cursor.executed if "INSERT INTO turnos" in q[0])
    assert "presencial" in insert[1]
    assert None in insert[1]


def test_un_turno_virtual_sin_enlace_no_llega_a_la_base(client, monkeypatch):
    """Se corta antes de escribir, no despues."""
    respuesta, cursor = _crear_turno(client, monkeypatch, {**BASE, "modalidad": "virtual"})

    assert respuesta.status_code == 400
    assert not any("INSERT INTO turnos" in q[0] for q in cursor.executed)
