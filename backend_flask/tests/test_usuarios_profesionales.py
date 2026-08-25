"""Campos profesionales del usuario: sin ellos no se puede emitir una receta.

`_validar_payload()` en recetas_routes.py exige apellido, DNI, numero de
matricula y direccion del lugar de atencion. Antes esas columnas solo se podian
escribir con SQL a mano: el CRUD no las aceptaba y no habia ningun input en el
frontend, asi que el modulo de recetas era inutilizable.
"""

import pytest

from app.routes import usuarios_routes as ur
from conftest import MockUser, login_as, make_db


def _director(client):
    login_as(client, MockUser(user_id=1, rol="director"))


ALTA_MINIMA = {
    "nombre": "Ana Lopez",
    "username": "alopez",
    "email": "ana@cau.test",
    "password": "Segura2026!",
    "rol": "profesional",
}

PROFESIONALES = {
    "apellido": "Lopez",
    "dni": "30111222",
    "sexo": "F",
    "telefono": "1122334455",
    "matricula_tipo": "MN",
    "matricula_numero": "12345",
    "matricula_provincia": "Buenos Aires",
    "lugar_atencion_nombre": "Consultorio Central",
    "lugar_atencion_direccion": "Av. Siempreviva 742",
    "lugar_atencion_contacto": "1199887766",
    "lugar_atencion_email": "consultorio@cau.test",
}


# ------------------------------------------------------- normalizacion


def test_apellido_esta_entre_los_campos():
    """El fork lo omitia, pero la receta lo exige y no siempre se puede deducir
    del nombre: con un nombre de una sola palabra queda vacio."""
    assert "apellido" in ur.PROFESSIONAL_FIELDS


@pytest.mark.parametrize("sexo", ["M", "F", "X", "O"])
def test_los_cuatro_sexos_del_enum_se_conservan(sexo):
    """El fork validaba solo F/M/X y convertia 'O' a NULL en silencio."""
    assert ur._professional_values({"sexo": sexo})["sexo"] == sexo


def test_sexo_fuera_del_enum_queda_en_null():
    """Un valor invalido se guarda como NULL en vez de reventar con 1265."""
    assert ur._professional_values({"sexo": "Z"})["sexo"] is None


@pytest.mark.parametrize("tipo", ["MN", "MP", "OP"])
def test_los_tres_tipos_de_matricula(tipo):
    assert ur._professional_values({"matricula_tipo": tipo})["matricula_tipo"] == tipo


def test_campos_vacios_quedan_en_null():
    valores = ur._professional_values({"dni": "", "telefono": None})
    assert valores["dni"] is None
    assert valores["telefono"] is None


def test_professional_values_funciona_sobre_un_form():
    """Mi Perfil manda multipart por la foto, no JSON."""
    from werkzeug.datastructures import MultiDict

    valores = ur._professional_values(MultiDict([("dni", "123"), ("sexo", "M")]))
    assert valores["dni"] == "123"
    assert valores["sexo"] == "M"


# ------------------------------------------------------- especialidad


@pytest.mark.parametrize("rol", ["profesional", "director"])
def test_la_especialidad_se_guarda_para_quienes_prescriben(rol):
    """Un director que prescribe quedaba con especialidad NULL en la receta."""
    assert ur._normalizar_especialidad(rol, "clinica") == "CLINICA"


@pytest.mark.parametrize("rol", ["administrativo", "area"])
def test_la_especialidad_se_descarta_para_los_demas(rol):
    assert ur._normalizar_especialidad(rol, "clinica") is None


# ------------------------------------------------------- alta


def test_el_alta_guarda_los_campos_profesionales(client, monkeypatch):
    _director(client)
    conexion, cursor = make_db(monkeypatch, ur, fetchone_results=[None])

    respuesta = client.post("/api/usuarios", json={**ALTA_MINIMA, **PROFESIONALES})

    assert respuesta.status_code == 200
    insert = next(e for e in cursor.executed if "INSERT INTO usuarios" in e[0])
    for campo in ur.PROFESSIONAL_FIELDS:
        assert campo in insert[0], f"falta {campo} en el INSERT"
    assert "12345" in insert[1]
    assert "Av. Siempreviva 742" in insert[1]
    assert conexion.committed is True


def test_el_alta_sin_datos_profesionales_sigue_funcionando(client, monkeypatch):
    """Un administrativo no necesita matricula."""
    _director(client)
    conexion, _ = make_db(monkeypatch, ur, fetchone_results=[None])

    respuesta = client.post(
        "/api/usuarios", json={**ALTA_MINIMA, "rol": "administrativo"}
    )

    assert respuesta.status_code == 200
    assert conexion.committed is True


def test_el_alta_duplicada_cierra_la_conexion(client, monkeypatch):
    """El return temprano dejaba la conexión abierta."""
    _director(client)
    conexion, cursor = make_db(monkeypatch, ur, fetchone_results=[{"id": 9}])

    respuesta = client.post("/api/usuarios", json=ALTA_MINIMA)

    assert respuesta.status_code == 400
    assert not any("INSERT" in q for q in cursor.queries)
    assert conexion.closed is True


# ------------------------------------------------------- detalle


def test_el_detalle_trae_los_campos_profesionales(client, monkeypatch):
    """Sin esto, editar un usuario los mostraría vacíos y los borraría."""
    _director(client)
    fila = {"id": 2, "nombre": "Ana", "username": "a", "email": "a@x", "rol": "profesional",
            "especialidad": None, **PROFESIONALES}
    _, cursor = make_db(monkeypatch, ur, fetchone_results=[fila])

    respuesta = client.get("/api/usuarios/2")

    assert respuesta.status_code == 200
    select = cursor.queries[0]
    for campo in ur.PROFESSIONAL_FIELDS:
        assert campo in select, f"falta {campo} en el SELECT del detalle"


# ------------------------------------------------------- edicion


def test_la_edicion_actualiza_solo_lo_enviado(client, monkeypatch):
    _director(client)
    actual = {"id": 2, "username": "alopez", "email": "ana@cau.test"}
    _, cursor = make_db(monkeypatch, ur, fetchone_results=[actual])

    client.put("/api/usuarios/2", json={"matricula_numero": "99999"})

    update = next(e for e in cursor.executed if "UPDATE usuarios" in e[0])
    assert "matricula_numero=%s" in update[0]
    # No se tocan los campos que no vinieron
    assert "lugar_atencion_direccion=%s" not in update[0]
    assert "99999" in update[1]


def test_la_edicion_permite_limpiar_un_campo(client, monkeypatch):
    """Mandar el campo vacío lo pone en NULL; no mandarlo lo deja intacto."""
    _director(client)
    actual = {"id": 2, "username": "alopez", "email": "ana@cau.test"}
    _, cursor = make_db(monkeypatch, ur, fetchone_results=[actual])

    client.put("/api/usuarios/2", json={"telefono": ""})

    update = next(e for e in cursor.executed if "UPDATE usuarios" in e[0])
    assert "telefono=%s" in update[0]
    assert None in update[1]


def test_editar_usuario_inexistente_cierra_la_conexion(client, monkeypatch):
    _director(client)
    conexion, _ = make_db(monkeypatch, ur, fetchone_results=[None])

    respuesta = client.put("/api/usuarios/999", json={"nombre": "X"})

    assert respuesta.status_code == 404
    assert conexion.closed is True


# ------------------------------------------------------- perfil propio


def test_me_devuelve_los_campos_profesionales(client):
    """Mi Perfil hidrata el formulario desde acá."""
    login_as(client, MockUser(user_id=1, rol="profesional", **PROFESIONALES))

    datos = client.get("/api/usuarios/me").get_json()

    assert datos["matricula_numero"] == "12345"
    assert datos["lugar_atencion_direccion"] == "Av. Siempreviva 742"


def test_el_perfil_devuelve_el_mismo_payload_que_me(client):
    login_as(client, MockUser(user_id=1, rol="profesional", **PROFESIONALES))

    assert client.get("/api/usuario/perfil").get_json() == client.get("/api/usuarios/me").get_json()


def test_el_profesional_puede_editar_sus_propios_datos(client, monkeypatch, tmp_path):
    """Es quien conoce su matrícula y dónde atiende."""
    from app import app as flask_app

    monkeypatch.setattr(flask_app, "root_path", str(tmp_path))
    login_as(client, MockUser(user_id=1, rol="profesional"))
    conexion, cursor = make_db(monkeypatch, ur)

    respuesta = client.post(
        "/api/usuario/perfil",
        data={
            "nombre": "Ana Lopez",
            "email": "ana@cau.test",
            "matricula_numero": "77777",
            "lugar_atencion_direccion": "Nueva 123",
        },
    )

    assert respuesta.status_code == 200
    update = next(e for e in cursor.executed if "UPDATE usuarios" in e[0])
    assert "matricula_numero=%s" in update[0]
    assert "lugar_atencion_direccion=%s" in update[0]
    assert "77777" in update[1]
    assert conexion.committed is True


def test_el_perfil_no_pisa_los_campos_que_no_se_enviaron(client, monkeypatch, tmp_path):
    from app import app as flask_app

    monkeypatch.setattr(flask_app, "root_path", str(tmp_path))
    login_as(client, MockUser(user_id=1, rol="profesional"))
    _, cursor = make_db(monkeypatch, ur)

    client.post("/api/usuario/perfil", data={"nombre": "Ana", "email": "a@x.test"})

    update = next(e for e in cursor.executed if "UPDATE usuarios" in e[0])
    assert "matricula_numero=%s" not in update[0]
