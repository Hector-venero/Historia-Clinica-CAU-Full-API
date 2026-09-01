"""El panel, más allá de hoy.

Todo el panel respondía por **hoy**, que sirve para arrancar el día y para nada
más: no había forma de ver si el mes viene mejor o peor, ni cuánta gente falta
sin avisar.

Lo que estos tests fijan:

1. Que un `profesional` vea **lo suyo** y quien dirige vea el centro. Sin el
   filtro, un profesional leería el ausentismo de sus colegas como propio.
2. Que `SUM()` sobre cero filas —que devuelve NULL, no 0— no se cuele como
   `None` en el JSON ni reviente el porcentaje.
3. Que el rango se valide: un rango abierto invita a pedir cinco años de turnos
   en una consulta.
"""

import pytest

from app.routes import dashboard_routes as dr
from conftest import MockUser, login_as, make_db


def _resumen(**valores):
    """Una fila como la devuelve la consulta agrupada."""
    base = {"total": 0, "con_aviso": 0, "sin_aviso": 0, "atendidos": 0, "por_delante": 0}
    base.update(valores)
    return base


# ------------------------------------------------------------------- alcance


def test_un_profesional_ve_solo_sus_turnos(client, monkeypatch):
    login_as(client, MockUser(5, "profesional"))
    _conn, cur = make_db(
        monkeypatch, dr, fetchone_results=[_resumen()], fetchall_results=[[]]
    )

    r = client.get("/api/dashboard/periodo")

    assert r.status_code == 200
    assert r.get_json()["propio"] is True
    assert "t.usuario_id = %s" in " ".join(cur.queries[0].split())
    assert cur.executed[0][1][-1] == 5


def test_quien_dirige_ve_todo_el_centro(client, monkeypatch):
    login_as(client, MockUser(1, "director"))
    _conn, cur = make_db(
        monkeypatch, dr, fetchone_results=[_resumen()], fetchall_results=[[]]
    )

    r = client.get("/api/dashboard/periodo")

    assert r.get_json()["propio"] is False
    assert "t.usuario_id" not in " ".join(cur.queries[0].split())


# ----------------------------------------------------------- el periodo vacio


def test_un_periodo_sin_turnos_devuelve_ceros(client, monkeypatch):
    """SUM() sobre cero filas devuelve NULL, no 0.

    Sin convertirlo, el JSON llevaria `null` a las tarjetas y el porcentaje
    reventaria al dividir.
    """
    login_as(client, MockUser(1, "director"))
    make_db(
        monkeypatch,
        dr,
        fetchone_results=[{"total": 0, "con_aviso": None, "sin_aviso": None,
                           "atendidos": None, "por_delante": None}],
        fetchall_results=[[]],
    )

    datos = client.get("/api/dashboard/periodo").get_json()

    assert datos["con_aviso"] == 0
    assert datos["sin_aviso"] == 0
    assert datos["ausentismo"] == 0.0


# --------------------------------------------------------------- el porcentaje


def test_el_ausentismo_es_sobre_todo_lo_agendado(client, monkeypatch):
    """Sobre el total del periodo y no sobre los que ya pasaron: quien mira
    quiere saber cuanto de lo que agendo se perdio."""
    login_as(client, MockUser(1, "director"))
    make_db(
        monkeypatch,
        dr,
        fetchone_results=[
            _resumen(total=20, con_aviso=2, sin_aviso=3, atendidos=10, por_delante=5)
        ],
        fetchall_results=[[]],
    )

    datos = client.get("/api/dashboard/periodo").get_json()

    assert datos["ausentismo"] == 25.0  # (2 + 3) de 20


# ------------------------------------------------------------------- el rango


def test_por_defecto_mira_los_ultimos_30_dias(client, monkeypatch):
    login_as(client, MockUser(1, "director"))
    make_db(monkeypatch, dr, fetchone_results=[_resumen()], fetchall_results=[[]])

    datos = client.get("/api/dashboard/periodo").get_json()

    from datetime import date, datetime

    desde = datetime.strptime(datos["desde"], "%Y-%m-%d").date()
    hasta = datetime.strptime(datos["hasta"], "%Y-%m-%d").date()
    assert hasta == date.today()
    assert (hasta - desde).days == 29


@pytest.mark.parametrize(
    "consulta",
    [
        "?desde=ayer",
        "?hasta=2026-13-45",
        "?desde=2026-09-10&hasta=2026-09-01",   # al reves
        "?desde=2020-01-01&hasta=2026-09-01",   # seis anios de una
    ],
)
def test_rechaza_rangos_invalidos(client, monkeypatch, consulta):
    login_as(client, MockUser(1, "director"))
    make_db(monkeypatch, dr)

    assert client.get(f"/api/dashboard/periodo{consulta}").status_code == 400
