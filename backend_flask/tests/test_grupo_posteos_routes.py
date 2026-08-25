"""Posteos internos de un grupo profesional.

Solo acceden los miembros del grupo, mas director y administrativo. Es el
control mas delicado del modulo: un posteo de grupo puede contener discusion
clinica sobre pacientes, y no debe verlo alguien ajeno al equipo tratante.
"""

import pytest

from app.routes import grupo_posteos_routes as posteos
from conftest import MockUser, login_as, make_db

POSTEO = {
    "id": 1,
    "grupo_id": 5,
    "titulo": "Reunión",
    "contenido": "Nos juntamos el viernes",
    "autor_id": 3,
    "creado_en": "2026-08-25 10:00:00",
    "actualizado_en": "2026-08-25 10:00:00",
    "autor_nombre": "Ana",
    "autor_rol": "profesional",
}

GRUPO_EXISTE = {"id": 5}
ES_MIEMBRO = {"1": 1}


def _login(client, rol, user_id=1):
    login_as(client, MockUser(user_id=user_id, rol=rol))


# ------------------------------------------------------------- acceso


def test_grupo_inexistente_devuelve_404(client, monkeypatch):
    _login(client, "director")
    make_db(monkeypatch, posteos, fetchone_results=[None])

    assert client.get("/api/grupos/999/posteos").status_code == 404


def test_un_no_miembro_no_puede_ver_los_posteos(client, monkeypatch):
    """Un profesional ajeno al grupo no accede: puede haber datos clínicos."""
    _login(client, "profesional", user_id=99)
    # 1) el grupo existe  2) no es miembro
    make_db(monkeypatch, posteos, fetchone_results=[GRUPO_EXISTE, None])

    respuesta = client.get("/api/grupos/5/posteos")

    assert respuesta.status_code == 403


def test_un_miembro_si_puede_ver(client, monkeypatch):
    _login(client, "profesional", user_id=3)
    make_db(
        monkeypatch,
        posteos,
        fetchone_results=[GRUPO_EXISTE, ES_MIEMBRO],
        fetchall_results=[[dict(POSTEO)]],
    )

    respuesta = client.get("/api/grupos/5/posteos")

    assert respuesta.status_code == 200
    assert respuesta.get_json()[0]["titulo"] == "Reunión"


@pytest.mark.parametrize("rol", ["director", "administrativo"])
def test_la_gestion_accede_sin_ser_miembro(client, monkeypatch, rol):
    _login(client, rol)
    # Solo se consulta la existencia del grupo: no se chequea membresia.
    make_db(
        monkeypatch,
        posteos,
        fetchone_results=[GRUPO_EXISTE],
        fetchall_results=[[dict(POSTEO)]],
    )

    assert client.get("/api/grupos/5/posteos").status_code == 200


def test_requiere_login(client):
    assert client.get("/api/grupos/5/posteos").status_code == 401


# ------------------------------------------------------------- publicar


def test_un_miembro_puede_postear(client, monkeypatch):
    _login(client, "profesional", user_id=3)
    conexion, cursor = make_db(
        monkeypatch, posteos, fetchone_results=[GRUPO_EXISTE, ES_MIEMBRO]
    )

    respuesta = client.post(
        "/api/grupos/5/posteos", json={"titulo": "Aviso", "contenido": "Texto"}
    )

    assert respuesta.status_code == 201
    assert any("INSERT INTO grupo_posteos" in q for q in cursor.queries)
    assert conexion.committed is True


def test_un_no_miembro_no_puede_postear(client, monkeypatch):
    _login(client, "profesional", user_id=99)
    _, cursor = make_db(monkeypatch, posteos, fetchone_results=[GRUPO_EXISTE, None])

    respuesta = client.post(
        "/api/grupos/5/posteos", json={"titulo": "Aviso", "contenido": "Texto"}
    )

    assert respuesta.status_code == 403
    assert not any("INSERT" in q for q in cursor.queries)


def test_rechaza_contenido_vacio(client, monkeypatch):
    _login(client, "profesional", user_id=3)
    _, cursor = make_db(monkeypatch, posteos, fetchone_results=[GRUPO_EXISTE, ES_MIEMBRO])

    respuesta = client.post("/api/grupos/5/posteos", json={"titulo": "Aviso", "contenido": "  "})

    assert respuesta.status_code == 400
    assert not any("INSERT" in q for q in cursor.queries)


def test_el_autor_es_el_usuario_logueado(client, monkeypatch):
    _login(client, "profesional", user_id=42)
    _, cursor = make_db(monkeypatch, posteos, fetchone_results=[GRUPO_EXISTE, ES_MIEMBRO])

    client.post("/api/grupos/5/posteos", json={"titulo": "A", "contenido": "B"})

    insert = next(e for e in cursor.executed if "INSERT INTO grupo_posteos" in e[0])
    assert 42 in insert[1]
