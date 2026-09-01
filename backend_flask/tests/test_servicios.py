"""Servicios (prestaciones): que la duracion del turno salga de lo que se pide.

Lo que estos tests cuidan, en orden de importancia:

1. **Un consultorio sin servicios funciona exactamente como antes.** Es la
   condicion que permitio soltar esto sin migrar a nadie, y la que se rompe sin
   que nadie lo note: alcanza con que una consulta nueva devuelva 0 en vez de
   None para que todos los turnos pasen a durar lo que no duran.
2. Que el servicio se valide **en el servidor**. El id viaja en el pedido, y con
   uno cualquiera se agendaria una duracion que ese profesional no ofrece.
3. Que un profesional no pueda tocar los servicios de un colega: seria cambiarle
   la agenda.
"""

import pytest

from app.routes import servicios_routes as sr
from app.routes import turnos_routes as tr
from conftest import MockUser, login_as, make_db


# ------------------------------------------------ de donde sale la duracion


def test_sin_servicio_la_duracion_es_la_del_profesional(monkeypatch):
    """El caso por defecto: nadie cargo servicios y todo sigue igual."""
    make_db(monkeypatch, tr, fetchone_results=[{"duracion_turno": 25}])

    assert tr._obtener_duracion_turno(1) == 25


def test_con_servicio_manda_el_servicio(monkeypatch):
    """Primero se busca el servicio; si aparece, no se consulta al profesional."""
    make_db(
        monkeypatch,
        tr,
        fetchone_results=[
            {"id": 7, "nombre": "Primera consulta", "duracion_minutos": 40, "precio": None},
        ],
    )

    assert tr._obtener_duracion_turno(1, 7) == 40


def test_un_servicio_de_otro_profesional_no_cambia_la_duracion(monkeypatch):
    """La consulta filtra por profesional, asi que no devuelve fila.

    Sin ese filtro, mandar el id de un servicio ajeno agendaria con su duracion.
    """
    make_db(
        monkeypatch,
        tr,
        fetchone_results=[None, {"duracion_turno": 20}],
    )

    assert tr._obtener_duracion_turno(1, 999) == 20


def test_servicio_no_numerico_no_rompe(monkeypatch):
    """El id llega del pedido: puede venir cualquier cosa."""
    make_db(monkeypatch, tr, fetchone_results=[{"duracion_turno": 30}])

    assert tr._obtener_duracion_turno(1, "no-es-un-id") == 30


def test_el_servicio_se_busca_solo_entre_los_activos(monkeypatch):
    """Un servicio discontinuado no puede seguir usandose para agendar."""
    _conn, db = make_db(monkeypatch, tr, fetchone_results=[None])

    tr.servicio_del_profesional(1, 5)

    consulta = " ".join(db.queries[0].split())
    assert "activo = 1" in consulta
    assert "usuario_id IS NULL OR usuario_id = %s" in consulta


# ------------------------------------------------------ validacion al crear


def test_no_se_agenda_con_un_servicio_que_no_existe(client, monkeypatch):
    """400 y no un turno con la duracion equivocada.

    Ignorar el servicio invalido en silencio dejaria el turno mal en la agenda
    sin que nadie se entere hasta el dia.
    """
    login_as(client, MockUser(1, "administrativo"))
    make_db(monkeypatch, tr, fetchone_results=[None])

    r = client.post(
        "/api/turnos",
        json={
            "paciente_id": 1,
            "usuario_id": 2,
            "fecha_inicio": "2026-09-07T09:00:00",
            "servicio_id": 999,
        },
    )

    assert r.status_code == 400
    assert "servicio" in r.get_json()["error"].lower()


# --------------------------------------------------------- catalogo: roles


def test_un_profesional_solo_crea_servicios_propios(client, monkeypatch):
    """Aunque mande el id de un colega, el servicio queda a su nombre."""
    login_as(client, MockUser(5, "profesional"))
    _conn, db = make_db(monkeypatch, sr)

    r = client.post(
        "/api/servicios",
        json={"nombre": "Control", "duracion_minutos": 15, "usuario_id": 99},
    )

    assert r.status_code == 201
    assert db.executed[0][1][0] == 5


def test_la_direccion_puede_crear_uno_del_consultorio(client, monkeypatch):
    """Sin usuario_id, el servicio es de todos: usuario_id queda en NULL."""
    login_as(client, MockUser(1, "director"))
    _conn, db = make_db(monkeypatch, sr)

    r = client.post("/api/servicios", json={"nombre": "Consulta", "duracion_minutos": 30})

    assert r.status_code == 201
    assert db.executed[0][1][0] is None


def test_un_profesional_no_edita_el_servicio_de_otro(client, monkeypatch):
    login_as(client, MockUser(5, "profesional"))
    make_db(monkeypatch, sr, fetchone_results=[{"id": 3, "usuario_id": 9}])

    r = client.put(
        "/api/servicios/3", json={"nombre": "Consulta", "duracion_minutos": 30}
    )

    assert r.status_code == 403


def test_borrar_es_baja_logica(client, monkeypatch):
    """Los turnos ya dados apuntan al servicio: borrarlo perderia con que se
    atendio el mes pasado."""
    login_as(client, MockUser(1, "director"))
    _conn, db = make_db(monkeypatch, sr, fetchone_results=[{"id": 3, "usuario_id": None}])

    r = client.delete("/api/servicios/3")

    assert r.status_code == 200
    assert "UPDATE servicios SET activo = 0" in " ".join(db.queries[-1].split())


# ------------------------------------------------------------- validacion


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"duracion_minutos": 30},                       # sin nombre
        {"nombre": "X"},                                # sin duracion
        {"nombre": "X", "duracion_minutos": 0},         # duracion imposible
        {"nombre": "X", "duracion_minutos": 10000},     # un turno de una semana
        {"nombre": "X", "duracion_minutos": 30, "precio": "gratis"},
        {"nombre": "X", "duracion_minutos": 30, "precio": -1},
    ],
)
def test_rechaza_datos_invalidos(client, monkeypatch, cuerpo):
    login_as(client, MockUser(1, "director"))
    make_db(monkeypatch, sr)

    assert client.post("/api/servicios", json=cuerpo).status_code == 400


def test_el_precio_puede_faltar(client, monkeypatch):
    """Muchos consultorios no quieren el precio cargado en el sistema.

    Obligarlo los dejaria afuera de los servicios enteros.
    """
    login_as(client, MockUser(1, "director"))
    _conn, db = make_db(monkeypatch, sr)

    r = client.post("/api/servicios", json={"nombre": "Consulta", "duracion_minutos": 30})

    assert r.status_code == 201
    assert db.executed[0][1][4] is None
