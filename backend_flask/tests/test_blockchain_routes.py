"""Verificacion contra la TSA: tres estados, no dos.

La TSA agrupa hashes en lotes y los ancla cada varios minutos. Entre el sellado
y su confirmacion responde `pending`, que no significa que el documento este
adulterado. La version anterior colapsaba cualquier no-exito (y tambien los
timeouts de red) a "invalido": mostraba "la historia fue modificada" sobre una
historia intacta y dejaba esa conclusion escrita en la tabla de auditoria, que
es un registro legal.

Estos tests fijan que solo se audite cuando hay un veredicto real.
"""

import requests

from app import app as flask_app
from app.routes import blockchain_routes
from conftest import MockUser, login_as, make_db

RECIBO = "cmQtZGUtcHJ1ZWJh"
HASH = "a" * 64

ANCLAJE = {
    "id": 10,
    "historia_id": 5,
    "hash_local": HASH,
    "hash_version": 2,
    "recibo_tsa": RECIBO,
    "estado": "pendiente",
}


def _login(client, rol="director"):
    login_as(client, MockUser(user_id=1, rol=rol, username="admin"))


def _auditorias(cursor):
    return [q for q in cursor.queries if "INSERT INTO auditorias_blockchain" in q]


def _respuesta_tsa(monkeypatch, payload):
    monkeypatch.setattr(blockchain_routes, "verificar_hash_en_bfa", lambda h, rd: payload)


# ----------------------------------------------------------- pendiente


def test_pendiente_no_se_reporta_como_adulterado(client, monkeypatch):
    _login(client)
    _, cursor = make_db(monkeypatch, blockchain_routes, fetchone_results=[ANCLAJE])
    _respuesta_tsa(monkeypatch, {"status": "pending", "messages": "batch abierto"})

    respuesta = client.get("/api/blockchain/verificar/historia/7")
    datos = respuesta.get_json()

    assert respuesta.status_code == 200
    assert datos["estado"] == "pendiente"
    assert datos["valido"] is None
    assert "modificada" not in datos["mensaje"].lower()


def test_pendiente_no_escribe_auditoria(client, monkeypatch):
    """La auditoria registra conclusiones, no intentos."""
    _login(client)
    _, cursor = make_db(monkeypatch, blockchain_routes, fetchone_results=[ANCLAJE])
    _respuesta_tsa(monkeypatch, {"status": "pending"})

    client.get("/api/blockchain/verificar/historia/7")

    assert _auditorias(cursor) == []


# ----------------------------------------------------------- confirmado


def test_confirmado_es_valido_y_audita(client, monkeypatch):
    _login(client)
    _, cursor = make_db(monkeypatch, blockchain_routes, fetchone_results=[ANCLAJE])
    _respuesta_tsa(
        monkeypatch,
        {"status": "success", "attestation_time": "2026-08-24T10:00:00", "permanent_rd": ""},
    )

    datos = client.get("/api/blockchain/verificar/historia/7").get_json()

    assert datos["estado"] == "confirmado"
    assert datos["valido"] is True
    assert len(_auditorias(cursor)) == 1


# ----------------------------------------------------------- failure


def test_failure_es_invalido_y_audita(client, monkeypatch):
    _login(client)
    _, cursor = make_db(monkeypatch, blockchain_routes, fetchone_results=[ANCLAJE])
    _respuesta_tsa(monkeypatch, {"status": "failure", "messages": "no coincide"})

    datos = client.get("/api/blockchain/verificar/historia/7").get_json()

    assert datos["estado"] == "error"
    assert datos["valido"] is False
    assert len(_auditorias(cursor)) == 1


# ----------------------------------------------------------- red caida


def test_error_de_red_no_concluye_nada(client, monkeypatch):
    """Un timeout es un problema de conectividad, no un veredicto de integridad."""
    _login(client)
    _, cursor = make_db(monkeypatch, blockchain_routes, fetchone_results=[ANCLAJE])

    def _falla(hash_local, rd):
        raise requests.ConnectionError("la TSA no responde")

    monkeypatch.setattr(blockchain_routes, "verificar_hash_en_bfa", _falla)

    respuesta = client.get("/api/blockchain/verificar/historia/7")
    datos = respuesta.get_json()

    assert respuesta.status_code == 503
    assert datos["valido"] is None
    assert datos["estado"] == "indeterminado"
    assert _auditorias(cursor) == []


def test_error_de_red_no_toca_el_anclaje(client, monkeypatch):
    _login(client)
    _, cursor = make_db(monkeypatch, blockchain_routes, fetchone_results=[ANCLAJE])
    monkeypatch.setattr(
        blockchain_routes,
        "verificar_hash_en_bfa",
        lambda h, rd: (_ for _ in ()).throw(requests.Timeout("timeout")),
    )

    client.get("/api/blockchain/verificar/historia/7")

    assert not any("UPDATE anclajes_historia" in q for q in cursor.queries)


# ----------------------------------------------------------- sin anclaje


def test_sin_anclaje_devuelve_400(client, monkeypatch):
    _login(client)
    make_db(monkeypatch, blockchain_routes, fetchone_results=[None])

    respuesta = client.get("/api/blockchain/verificar/historia/7")

    assert respuesta.status_code == 400
    assert "sellado" in respuesta.get_json()["error"].lower()


# ----------------------------------------------------------- sellado


def test_sellar_registra_un_anclaje_nuevo(client, monkeypatch):
    """Append-only: cada sellado agrega una fila, nunca pisa la anterior."""
    _login(client)
    historia = {"id": 5, "paciente_id": 7, "hash_local": HASH, "hash_version": 2}
    _, cursor = make_db(monkeypatch, blockchain_routes, fetchone_results=[historia])
    monkeypatch.setattr(blockchain_routes, "registrar_hash_en_bfa", lambda h: RECIBO)

    respuesta = client.post("/api/blockchain/registrar/5")

    assert respuesta.status_code == 201
    assert respuesta.get_json()["recibo_tsa"] == RECIBO
    assert any("INSERT INTO anclajes_historia" in q for q in cursor.queries)
    # Nunca un UPDATE que pise el recibo anterior
    assert not any("UPDATE anclajes_historia SET recibo_tsa" in q for q in cursor.queries)


def test_sellar_sin_hash_local_no_llama_a_la_tsa(client, monkeypatch):
    _login(client)
    historia = {"id": 5, "paciente_id": 7, "hash_local": None}
    make_db(monkeypatch, blockchain_routes, fetchone_results=[historia])

    llamadas = []
    monkeypatch.setattr(
        blockchain_routes, "registrar_hash_en_bfa", lambda h: llamadas.append(h)
    )

    respuesta = client.post("/api/blockchain/registrar/5")

    assert respuesta.status_code == 400
    assert llamadas == []


def test_sellar_requiere_rol(client, monkeypatch):
    _login(client, rol="administrativo")
    make_db(monkeypatch, blockchain_routes)

    assert client.post("/api/blockchain/registrar/5").status_code == 403


# ----------------------------------------------------------- evolucion


def test_verificar_evolucion_devuelve_501_en_vez_de_un_falso_negativo(client):
    """Antes verificaba el hash de la evolucion contra el recibo de la historia.

    Son dos hashes distintos, asi que la TSA respondia failure siempre y la
    ruta mostraba "evolucion modificada" sobre evoluciones intactas.
    """
    _login(client)

    respuesta = client.get("/api/blockchain/verificar/evolucion/3")
    datos = respuesta.get_json()

    assert respuesta.status_code == 501
    assert datos["valido"] is None
    assert datos["estado"] == "no_implementado"


# ----------------------------------------------------------- test_tx


def test_test_tx_requiere_login(client):
    assert client.get("/api/blockchain/test_tx").status_code == 401


def test_test_tx_rechaza_rol_no_director(client):
    _login(client, rol="profesional")
    assert client.get("/api/blockchain/test_tx").status_code == 403


def test_test_tx_apagado_no_sella(client, monkeypatch):
    """Con el flag apagado no se llega a consumir cuota de la TSA."""
    _login(client)
    monkeypatch.setitem(flask_app.config, "ENABLE_BLOCKCHAIN_TEST_ENDPOINTS", False)

    llamadas = []
    monkeypatch.setattr(
        blockchain_routes, "registrar_hash_en_bfa", lambda h: llamadas.append(h)
    )

    respuesta = client.get("/api/blockchain/test_tx")

    assert respuesta.status_code == 403
    assert llamadas == []


def test_test_tx_encendido_sella(client, monkeypatch):
    _login(client)
    monkeypatch.setitem(flask_app.config, "ENABLE_BLOCKCHAIN_TEST_ENDPOINTS", True)
    monkeypatch.setattr(blockchain_routes, "registrar_hash_en_bfa", lambda h: RECIBO)

    respuesta = client.get("/api/blockchain/test_tx")

    assert respuesta.status_code == 200
    assert respuesta.get_json()["recibo_tsa"] == RECIBO
