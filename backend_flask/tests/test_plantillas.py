"""Plantillas de texto clinico.

Lo que se escribe seguido, guardado una vez. Lo delicado no es el CRUD sino
**quien ve que**: la lista que se ofrece al escribir una evolucion tiene que ser
la del profesional que escribe mas las del consultorio, y nada mas. Con el
filtro mal, un profesional veria los textos con los que otro describe a sus
pacientes.
"""

import pytest

from app.routes import plantillas_routes as pr
from conftest import MockUser, login_as, make_db


# ------------------------------------------------------------------ que se ve


def test_al_escribir_solo_se_ofrecen_las_propias_y_las_del_consultorio(client, monkeypatch):
    login_as(client, MockUser(5, "profesional"))
    _conn, cur = make_db(monkeypatch, pr, fetchall_results=[[]])

    client.get("/api/plantillas?campo=evolucion")

    consulta = " ".join(cur.queries[0].split())
    assert "usuario_id IS NULL OR p.usuario_id = %s" in consulta
    assert "p.activo = 1" in consulta
    assert cur.executed[0][1] == ("evolucion", 5)


def test_administrarlas_muestra_el_catalogo_entero(client, monkeypatch):
    """La pantalla de configurar tiene que ver tambien las inactivas."""
    login_as(client, MockUser(1, "director"))
    _conn, cur = make_db(monkeypatch, pr, fetchall_results=[[]])

    client.get("/api/plantillas?todas=1")

    consulta = " ".join(cur.queries[0].split())
    assert "WHERE" not in consulta  # sin filtro: ni por activo ni por usuario
    assert cur.executed[0][1] == ()


# ------------------------------------------------------------------- permisos


def test_un_administrativo_no_define_plantillas_clinicas(client, monkeypatch):
    """No redacta evoluciones, asi que tampoco los textos con los que se
    redactan."""
    login_as(client, MockUser(1, "administrativo"))
    make_db(monkeypatch, pr)

    r = client.post("/api/plantillas", json={"nombre": "X", "cuerpo": "Y"})

    assert r.status_code == 403


def test_un_profesional_solo_crea_las_suyas(client, monkeypatch):
    """Aunque mande el id de un colega."""
    login_as(client, MockUser(5, "profesional"))
    _conn, cur = make_db(monkeypatch, pr)

    r = client.post(
        "/api/plantillas",
        json={"nombre": "Control", "cuerpo": "Sin novedades.", "usuario_id": 99},
    )

    assert r.status_code == 201
    assert cur.executed[0][1][0] == 5


def test_un_profesional_no_borra_la_de_otro(client, monkeypatch):
    login_as(client, MockUser(5, "profesional"))
    make_db(monkeypatch, pr, fetchone_results=[{"id": 3, "usuario_id": 9}])

    assert client.delete("/api/plantillas/3").status_code == 403


def test_la_direccion_crea_una_del_consultorio(client, monkeypatch):
    """usuario_id NULL: la pauta de alarma la escribe una vez y la usa todo el
    equipo."""
    login_as(client, MockUser(1, "director"))
    _conn, cur = make_db(monkeypatch, pr)

    r = client.post("/api/plantillas", json={"nombre": "Pauta", "cuerpo": "Consultar si..."})

    assert r.status_code == 201
    assert cur.executed[0][1][0] is None


# ----------------------------------------------------------------- validacion


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"cuerpo": "algo"},                                   # sin nombre
        {"nombre": "X"},                                      # sin texto
        {"nombre": "X", "cuerpo": "   "},                     # solo espacios
        {"nombre": "X", "cuerpo": "y", "campo": "inventado"}, # campo que no existe
        {"nombre": "X", "cuerpo": "y" * 5001},                # una novela
    ],
)
def test_rechaza_datos_invalidos(client, monkeypatch, cuerpo):
    login_as(client, MockUser(1, "director"))
    make_db(monkeypatch, pr)

    assert client.post("/api/plantillas", json=cuerpo).status_code == 400


def test_borrar_borra_de_verdad(client, monkeypatch):
    """A diferencia de `servicios`, no queda referenciada por nada: lo que se
    guarda en la evolucion es el texto copiado, no un puntero."""
    login_as(client, MockUser(1, "director"))
    _conn, cur = make_db(monkeypatch, pr, fetchone_results=[{"id": 3, "usuario_id": None}])

    r = client.delete("/api/plantillas/3")

    assert r.status_code == 200
    assert any("DELETE FROM plantillas_texto" in q for q in cur.queries)
