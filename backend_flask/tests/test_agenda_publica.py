"""Publicar la agenda: lo que no se puede publicar a medias.

Encender `agenda_publica` es el momento exacto en que los datos de un
profesional pasan a estar a la vista de desconocidos en el directorio. Lo que se
exige acá no es burocracia: es lo que el paciente va a leer para decidir con
quién se atiende.
"""

from app.routes import agenda_publica_routes as ap
from conftest import MockUser, login_as, make_db


FILA_COMPLETA = {
    "agenda_publica": 0,
    "presentacion_publica": None,
    "especialidad": "Odontologia",
    "apellido": "Lopez",
    "duracion_turno": 30,
    "lugar_atencion_nombre": "Consultorio",
    "lugar_atencion_direccion": "Av. Rivadavia 1234",
}


def _preparar(client, monkeypatch, fila):
    monkeypatch.setattr(ap, "cliente_actual", lambda: None)
    _conn, cursor = make_db(monkeypatch, ap, fetchone_results=[fila, fila])
    login_as(client, MockUser(1, "director"))
    return cursor


def test_no_se_publica_sin_apellido(client, monkeypatch):
    """El alta crea el usuario con el nombre del consultorio, asi que sin
    apellido el paciente veria "Consultorio Dr. Lopez" como su profesional."""
    cursor = _preparar(client, monkeypatch, {**FILA_COMPLETA, "apellido": None})

    respuesta = client.post("/api/agenda-publica", json={"activa": True})

    assert respuesta.status_code == 400
    assert "apellido" in respuesta.get_json()["error"]
    assert not any("UPDATE usuarios" in q[0] for q in cursor.executed)


def test_se_informan_todos_los_faltantes_juntos(client, monkeypatch):
    """Guardar cuatro veces para que cada vez falte otra cosa es exasperante."""
    _preparar(
        client, monkeypatch,
        {**FILA_COMPLETA, "apellido": None, "especialidad": None},
    )

    respuesta = client.post("/api/agenda-publica", json={"activa": True})

    faltantes = respuesta.get_json()["faltantes"]
    assert len(faltantes) == 2


def test_el_apellido_del_mismo_pedido_alcanza(client, monkeypatch):
    """Si lo completa en el formulario no tiene por que guardar dos veces."""
    cursor = _preparar(client, monkeypatch, {**FILA_COMPLETA, "apellido": None})

    respuesta = client.post(
        "/api/agenda-publica", json={"activa": True, "apellido": "Lopez"}
    )

    assert respuesta.status_code == 200
    assert any("UPDATE usuarios" in q[0] for q in cursor.executed)


def test_apagar_la_agenda_no_exige_nada(client, monkeypatch):
    """Un perfil incompleto no puede dejar a alguien atrapado en el directorio."""
    cursor = _preparar(client, monkeypatch, {**FILA_COMPLETA, "apellido": None})

    respuesta = client.post("/api/agenda-publica", json={"activa": False})

    assert respuesta.status_code == 200
    assert any("UPDATE usuarios" in q[0] for q in cursor.executed)
