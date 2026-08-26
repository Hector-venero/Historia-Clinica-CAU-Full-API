"""Comunicados internos: quien lee y quien publica.

Los lee cualquier usuario autenticado; publicar y borrar queda restringido a
director y administrativo.
"""

import pytest

from app.routes import comunicados_routes
from conftest import MockUser, login_as, make_db

COMUNICADO = {
    "id": 1,
    "titulo": "Cambio de horario",
    "contenido": "A partir del lunes...",
    "autor_id": 1,
    "creado_en": "2026-08-24 10:00:00",
    "actualizado_en": "2026-08-24 10:00:00",
    "autor_nombre": "Admin",
    "autor_rol": "director",
}


def _login(client, rol):
    login_as(client, MockUser(user_id=1, rol=rol))


# ---------------------------------------------------------------- lectura


@pytest.mark.parametrize("rol", ["director", "profesional", "administrativo", "area"])
def test_todos_los_roles_pueden_leer(client, monkeypatch, rol):
    _login(client, rol)
    make_db(monkeypatch, comunicados_routes, fetchall_results=[[dict(COMUNICADO)]])

    respuesta = client.get("/api/comunicados")

    assert respuesta.status_code == 200
    assert respuesta.get_json()[0]["titulo"] == "Cambio de horario"


@pytest.mark.parametrize(
    "rol, esperado",
    [("director", True), ("administrativo", True), ("profesional", False), ("area", False)],
)
def test_puede_eliminar_refleja_el_rol(client, monkeypatch, rol, esperado):
    """Es un dato para la UI; el permiso real lo aplica @requiere_rol en el DELETE."""
    _login(client, rol)
    make_db(monkeypatch, comunicados_routes, fetchall_results=[[dict(COMUNICADO)]])

    datos = client.get("/api/comunicados").get_json()

    assert datos[0]["puede_eliminar"] is esperado


def test_listar_requiere_login(client):
    assert client.get("/api/comunicados").status_code == 401


# ---------------------------------------------------------------- publicar


@pytest.mark.parametrize("rol", ["director", "administrativo"])
def test_los_publicadores_pueden_crear(client, monkeypatch, rol):
    _login(client, rol)
    conexion, cursor = make_db(monkeypatch, comunicados_routes)

    respuesta = client.post(
        "/api/comunicados", json={"titulo": "Aviso", "contenido": "Texto"}
    )

    assert respuesta.status_code == 201
    assert any("INSERT INTO comunicados" in q for q in cursor.queries)
    assert conexion.committed is True


@pytest.mark.parametrize("rol", ["profesional", "area"])
def test_los_demas_roles_no_pueden_crear(client, monkeypatch, rol):
    _login(client, rol)
    _, cursor = make_db(monkeypatch, comunicados_routes)

    respuesta = client.post(
        "/api/comunicados", json={"titulo": "Aviso", "contenido": "Texto"}
    )

    assert respuesta.status_code == 403
    assert not any("INSERT" in q for q in cursor.queries)


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"titulo": "", "contenido": "Texto"},
        {"titulo": "Aviso", "contenido": ""},
        {"titulo": "   ", "contenido": "   "},
        {},
    ],
)
def test_rechaza_titulo_o_contenido_vacios(client, monkeypatch, cuerpo):
    _login(client, "director")
    _, cursor = make_db(monkeypatch, comunicados_routes)

    respuesta = client.post("/api/comunicados", json=cuerpo)

    assert respuesta.status_code == 400
    assert not any("INSERT" in q for q in cursor.queries)


def test_el_autor_es_el_usuario_logueado(client, monkeypatch):
    login_as(client, MockUser(user_id=42, rol="director"))
    _, cursor = make_db(monkeypatch, comunicados_routes)

    client.post("/api/comunicados", json={"titulo": "Aviso", "contenido": "Texto"})

    insert = next(e for e in cursor.executed if "INSERT INTO comunicados" in e[0])
    assert insert[1][2] == 42


# ---------------------------------------------------------------- borrar


def test_eliminar_comunicado_existente(client, monkeypatch):
    _login(client, "director")
    conexion, cursor = make_db(monkeypatch, comunicados_routes, fetchone_results=[{"id": 3}])

    respuesta = client.delete("/api/comunicados/3")

    assert respuesta.status_code == 200
    assert any("DELETE FROM comunicados" in q for q in cursor.queries)
    assert conexion.committed is True


def test_eliminar_inexistente_devuelve_404_y_cierra(client, monkeypatch):
    _login(client, "director")
    conexion, cursor = make_db(monkeypatch, comunicados_routes, fetchone_results=[None])

    respuesta = client.delete("/api/comunicados/999")

    assert respuesta.status_code == 404
    assert not any("DELETE" in q for q in cursor.queries)
    assert conexion.closed is True


def test_un_profesional_no_puede_eliminar(client, monkeypatch):
    _login(client, "profesional")
    _, cursor = make_db(monkeypatch, comunicados_routes, fetchone_results=[{"id": 3}])

    assert client.delete("/api/comunicados/3").status_code == 403
    assert not any("DELETE" in q for q in cursor.queries)


# ------------------------------------------------- notificaciones

# La prioridad decide los canales: `normal` solo aparece en la campana,
# `importante` ademas manda un mail. Mandar mail por cada aviso convierte la
# casilla en ruido y termina logrando que no se lean los que si importan.


def _sin_mails(monkeypatch):
    """Intercepta el envio y registra a quien se le habria mandado."""
    enviados = []
    monkeypatch.setattr(
        comunicados_routes,
        "enviar_aviso_comunicado",
        lambda destinatarios, titulo, contenido, autor: enviados.append(
            {"destinatarios": destinatarios, "titulo": titulo, "autor": autor}
        ),
    )
    return enviados


@pytest.mark.parametrize("prioridad", ["normal", "importante"])
def test_prioridades_validas_se_aceptan(client, monkeypatch, prioridad):
    _login(client, "director")
    make_db(monkeypatch, comunicados_routes, fetchall_results=[[]])
    _sin_mails(monkeypatch)

    respuesta = client.post(
        "/api/comunicados", json={"titulo": "T", "contenido": "C", "prioridad": prioridad}
    )

    assert respuesta.status_code == 201
    assert respuesta.get_json()["prioridad"] == prioridad


def test_prioridad_invalida_se_rechaza_sin_escribir(client, monkeypatch):
    """Un valor libre no puede llegar a la base: la columna es VARCHAR y lo
    aceptaria sin chistar, dejando un comunicado en un estado que nadie maneja."""
    _login(client, "director")
    _, cursor = make_db(monkeypatch, comunicados_routes)
    _sin_mails(monkeypatch)

    respuesta = client.post(
        "/api/comunicados", json={"titulo": "T", "contenido": "C", "prioridad": "urgentisimo"}
    )

    assert respuesta.status_code == 400
    assert not any("INSERT INTO comunicados" in q for q in cursor.queries)


def test_sin_prioridad_queda_en_normal(client, monkeypatch):
    _login(client, "director")
    make_db(monkeypatch, comunicados_routes, fetchall_results=[[]])
    enviados = _sin_mails(monkeypatch)

    respuesta = client.post("/api/comunicados", json={"titulo": "T", "contenido": "C"})

    assert respuesta.get_json()["prioridad"] == "normal"
    assert enviados == []


def test_un_comunicado_normal_no_manda_mail(client, monkeypatch):
    _login(client, "director")
    make_db(monkeypatch, comunicados_routes, fetchall_results=[[]])
    enviados = _sin_mails(monkeypatch)

    client.post(
        "/api/comunicados", json={"titulo": "T", "contenido": "C", "prioridad": "normal"}
    )

    assert enviados == []


def test_un_comunicado_importante_manda_mail_a_los_demas(client, monkeypatch):
    _login(client, "director")
    make_db(
        monkeypatch,
        comunicados_routes,
        fetchall_results=[[("uno@cau.test",), ("dos@cau.test",)]],
    )
    enviados = _sin_mails(monkeypatch)

    respuesta = client.post(
        "/api/comunicados",
        json={"titulo": "Cierre", "contenido": "C", "prioridad": "importante"},
    )

    assert respuesta.get_json()["avisados"] == 2
    assert enviados[0]["destinatarios"] == ["uno@cau.test", "dos@cau.test"]
    assert enviados[0]["titulo"] == "Cierre"


def test_los_destinatarios_excluyen_inactivos_y_al_autor(client, monkeypatch):
    """Un usuario dado de baja no deberia seguir recibiendo comunicacion
    interna, y el autor no necesita que le avisen de lo que acaba de escribir."""
    _login(client, "director")
    _, cursor = make_db(monkeypatch, comunicados_routes, fetchall_results=[[]])
    _sin_mails(monkeypatch)

    client.post(
        "/api/comunicados", json={"titulo": "T", "contenido": "C", "prioridad": "importante"}
    )

    consulta = next(q for q in cursor.queries if "SELECT email FROM usuarios" in q)
    assert "activo = 1" in consulta
    assert "id <> %s" in consulta


def test_el_autor_queda_marcado_como_leido(client, monkeypatch):
    """Sin esto el contador de la campana le queda en 1 al autor apenas publica."""
    _login(client, "director")
    _, cursor = make_db(monkeypatch, comunicados_routes, fetchall_results=[[]])
    _sin_mails(monkeypatch)

    client.post("/api/comunicados", json={"titulo": "T", "contenido": "C"})

    assert any("INSERT IGNORE INTO comunicado_lecturas" in q for q in cursor.queries)


def test_contar_no_leidos(client, monkeypatch):
    _login(client, "profesional")
    make_db(monkeypatch, comunicados_routes, fetchone_results=[{"cantidad": 3}])

    respuesta = client.get("/api/comunicados/no_leidos")

    assert respuesta.status_code == 200
    assert respuesta.get_json()["cantidad"] == 3


def test_marcar_leido_es_idempotente(client, monkeypatch):
    """Se usa INSERT IGNORE contra el UNIQUE: marcar dos veces no es un error."""
    _login(client, "profesional")
    conexion, cursor = make_db(monkeypatch, comunicados_routes, fetchone_results=[{"id": 1}])

    respuesta = client.post("/api/comunicados/1/leer")

    assert respuesta.status_code == 200
    assert any("INSERT IGNORE INTO comunicado_lecturas" in q for q in cursor.queries)
    assert conexion.committed is True


def test_marcar_leido_de_un_comunicado_inexistente(client, monkeypatch):
    _login(client, "profesional")
    conexion, cursor = make_db(monkeypatch, comunicados_routes, fetchone_results=[None])

    respuesta = client.post("/api/comunicados/999/leer")

    assert respuesta.status_code == 404
    assert not any("INSERT IGNORE" in q for q in cursor.queries)
    assert conexion.closed is True


def test_el_listado_informa_si_esta_leido(client, monkeypatch):
    """MySQL devuelve `IS NOT NULL` como 1/0; la UI espera un booleano."""
    _login(client, "profesional")
    fila = dict(COMUNICADO, prioridad="normal", leido=1)
    make_db(monkeypatch, comunicados_routes, fetchall_results=[[fila]])

    cuerpo = client.get("/api/comunicados").get_json()

    assert cuerpo[0]["leido"] is True
