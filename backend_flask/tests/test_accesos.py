"""Quien abrio la historia de quien.

No habia ningun registro. En un consultorio con direccion, varios
profesionales, secretaria y coordinacion de area —todos con acceso a datos de
pacientes— nadie podia responder "¿quien miro esta historia?".

Lo que estos tests fijan, y en este orden:

1. **Que anotar nunca rompa el pedido.** Un sistema clinico que deja de mostrar
   una historia porque no pudo escribir una fila de auditoria es peor que uno
   sin auditoria: en el medio hay alguien esperando ser atendido.
2. **Que se guarde quien/que/cuando y NUNCA el contenido.** Copiar lo leido aca
   seria duplicar la historia clinica en una segunda tabla.
3. **Que solo la direccion pueda leerlo.** Dice a que hora cada persona del
   equipo abrio que historia: es informacion sobre el personal, y repartirla
   convierte el control en vigilancia lateral entre companeros.
4. Que el modulo **no tenga** como borrar ni actualizar.
"""

import pytest

from app import accesos
from app.routes import accesos_routes as ar
from conftest import MockUser, login_as, make_db


# ---------------------------------------------------- anotar no puede romper


def test_si_falla_la_base_no_revienta(monkeypatch):
    """El profesional ve la historia igual."""
    make_db(monkeypatch, accesos, execute_side_effects=[RuntimeError("base caida")])

    accesos.registrar(1, accesos.VER_HISTORIA)


def test_un_paciente_id_invalido_no_revienta(monkeypatch):
    _conn, cur = make_db(monkeypatch, accesos)

    accesos.registrar("no-es-un-id", accesos.VER_HISTORIA)

    assert cur.executed == []


# ------------------------------------------------------------ que se guarda


def test_se_guarda_quien_que_y_cuando(monkeypatch):
    _conn, cur = make_db(monkeypatch, accesos)

    accesos.registrar(7, accesos.VER_HISTORIA, usuario_id=3, ip="1.2.3.4")

    consulta = " ".join(cur.queries[0].split())
    assert "INSERT INTO accesos_historia" in consulta
    usuario, paciente, accion, detalle, ip, _cuando = cur.executed[0][1]
    assert (usuario, paciente, accion, detalle, ip) == (3, 7, "ver_historia", None, "1.2.3.4")


def test_no_hay_ninguna_columna_de_contenido():
    """Copiar lo leido seria duplicar la historia clinica en una segunda tabla,
    con las mismas obligaciones legales y menos cuidado encima."""
    import inspect

    fuente = inspect.getsource(accesos.registrar)

    for prohibido in ("contenido", "resumen", "indicaciones", "diagnostico"):
        assert prohibido not in fuente


def test_los_textos_se_recortan_a_lo_que_entra(monkeypatch):
    """El detalle llega de un nombre de archivo, que puede venir de cualquier
    largo, y la columna tiene 255."""
    _conn, cur = make_db(monkeypatch, accesos)

    accesos.registrar(1, "a" * 100, detalle="b" * 900, usuario_id=1, ip="c" * 200)

    _u, _p, accion, detalle, ip, _cuando = cur.executed[0][1]
    assert len(accion) <= 30
    assert len(detalle) <= 255
    assert len(ip) <= 60


def test_un_paciente_del_portal_no_queda_como_usuario(monkeypatch, client):
    """Su id apunta a otra base: guardarlo aca senalaria a la persona
    equivocada del consultorio."""
    _conn, cur = make_db(monkeypatch, accesos)

    paciente = MockUser(3, "paciente")
    paciente.es_paciente = True
    login_as(client, paciente)

    with client.application.test_request_context("/"):
        from flask_login import login_user

        login_user(paciente)
        accesos.registrar(9, accesos.VER_HISTORIA)

    assert cur.executed[0][1][0] is None


# ------------------------------------------------------------- append-only


def test_el_modulo_no_sabe_borrar_ni_actualizar():
    """Un registro de accesos que el propio sistema puede reescribir no prueba
    nada. No es un olvido: es la propiedad que lo hace servir."""
    import inspect

    fuente = inspect.getsource(accesos)

    assert "DELETE FROM accesos_historia" not in fuente
    assert "UPDATE accesos_historia" not in fuente


# ---------------------------------------------------------------- permisos


@pytest.mark.parametrize("rol", ["profesional", "administrativo", "area"])
def test_solo_la_direccion_lee_el_registro(client, monkeypatch, rol):
    """Dice a que hora cada persona del equipo abrio que historia. Repartirlo
    convierte el control en vigilancia lateral entre companeros.

    Un `profesional` no lo ve ni de sus propios pacientes: la lista incluye lo
    que hicieron sus colegas con esa misma historia.
    """
    login_as(client, MockUser(1, rol))
    make_db(monkeypatch, ar)

    assert client.get("/api/pacientes/1/accesos").status_code == 403
    assert client.get("/api/usuarios/2/accesos").status_code == 403


def test_la_direccion_si(client, monkeypatch):
    login_as(client, MockUser(1, "director"))
    make_db(monkeypatch, accesos, fetchall_results=[[]])

    assert client.get("/api/pacientes/1/accesos").status_code == 200


def test_sin_sesion_no_se_lee(client):
    assert client.get("/api/pacientes/1/accesos").status_code == 401


# ------------------------------------------------------------------ limites


def test_el_limite_tiene_tope(client, monkeypatch):
    """Es una pantalla de revision, no una exportacion: pedir diez mil accesos
    sostiene la conexion sin ayudar a nadie."""
    login_as(client, MockUser(1, "director"))
    _conn, cur = make_db(monkeypatch, accesos, fetchall_results=[[]])

    client.get("/api/pacientes/1/accesos?limite=999999")

    assert cur.executed[0][1][1] == ar.TOPE


def test_un_limite_absurdo_no_rompe(client, monkeypatch):
    login_as(client, MockUser(1, "director"))
    _conn, cur = make_db(monkeypatch, accesos, fetchall_results=[[]])

    r = client.get("/api/pacientes/1/accesos?limite=-5")

    assert r.status_code == 200
    assert cur.executed[0][1][1] >= 1


# -------------------------------------------------------------- las dos vistas


def test_de_usuario_responde_la_otra_mitad(client, monkeypatch):
    """Lo que se investiga no suele ser "quien vio esta historia" sino "que
    estuvo mirando esta persona"."""
    login_as(client, MockUser(1, "director"))
    _conn, cur = make_db(monkeypatch, accesos, fetchall_results=[[]])

    client.get("/api/usuarios/4/accesos")

    consulta = " ".join(cur.queries[0].split())
    assert "WHERE a.usuario_id = %s" in consulta
    assert "JOIN pacientes p" in consulta


def test_la_fecha_sale_en_hora_argentina(monkeypatch):
    """jsonify serializa los DATETIME etiquetados como GMT aunque esten en hora
    argentina, y quien los lea como UTC los corre tres horas. Ya paso tres veces
    en este proyecto."""
    from datetime import datetime

    from app import app as flask_app

    fila = {
        "id": 1, "accion": "ver_historia", "detalle": None, "ip": None,
        "creado_en": datetime(2026, 9, 1, 10, 0, 0), "usuario_id": 2,
        "usuario": "Laura", "rol": "profesional",
    }

    with flask_app.app_context():
        salida = accesos._serializar(fila)

    assert salida["cuando"].endswith("-03:00")


def test_un_usuario_borrado_se_dice_no_se_deja_en_blanco(monkeypatch):
    from datetime import datetime

    from app import app as flask_app

    fila = {
        "id": 1, "accion": "ver_historia", "detalle": None, "ip": None,
        "creado_en": datetime(2026, 9, 1, 10, 0, 0), "usuario_id": None,
        "usuario": None, "rol": None,
    }

    with flask_app.app_context():
        salida = accesos._serializar(fila)

    assert salida["usuario"] == "—"


def test_el_texto_de_la_accion_lo_arma_el_servidor(monkeypatch):
    """Sumar una accion tiene que ser un solo lugar, no dos que se contradicen."""
    from datetime import datetime

    from app import app as flask_app

    fila = {
        "id": 1, "accion": accesos.EXPORTAR_HISTORIA, "detalle": None, "ip": None,
        "creado_en": datetime(2026, 9, 1, 10, 0, 0), "usuario_id": 2,
    }

    with flask_app.app_context():
        salida = accesos._serializar(fila)

    assert salida["accion_nombre"] == "Descargó la historia en PDF"
