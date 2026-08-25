"""Recetas electronicas: reglas de negocio y datos del profesional.

Las reglas (maximo 3 medicamentos, cantidad entre 1 y 2, diagnostico por
defecto) vienen de los requerimientos del CAU. Los tests las fijan para que no
se pierdan en un refactor.

Ademas cubren dos cosas que estaban hardcodeadas y ahora salen de la config o
del perfil del profesional: la URL del proveedor y el lugar de atencion.
"""

import json

import pytest

from app import app as flask_app
from app.routes import recetas_routes
from app.utils import qbi_client
from conftest import MockUser, login_as, make_db

PACIENTE = {
    "id": 4,
    "nombre": "Ana",
    "apellido": "Perez",
    "dni": "30111222",
    "sexo": "Femenino",
    "fecha_nacimiento": "1990-05-10",
    "email": "ana@example.com",
    "direccion": "Calle Falsa 123",
}

USUARIO = {
    "id": 1,
    "nombre": "Juan Lopez",
    "apellido": "Lopez",
    "email": "juan@cau.example",
    "dni": "20111222",
    "sexo": "M",
    "telefono": "1122334455",
    "profesion": "Medico",
    "matricula_tipo": "MN",
    "matricula_numero": "12345",
    "matricula_provincia": "Buenos Aires",
    "lugar_atencion_nombre": "Consultorio Central",
    "lugar_atencion_direccion": "Av. Siempreviva 742",
    "lugar_atencion_email": "consultorio@cau.example",
    "lugar_atencion_contacto": "1199887766",
}

RESPUESTA_QBI = {
    "recetas": [{"idReceta": "REC-1", "s3Link": "https://s3/receta.pdf"}],
    "response": [{"status": "emitida"}],
    "idTransaccion": "TX-1",
}


@pytest.fixture
def configurado(monkeypatch):
    monkeypatch.setitem(flask_app.config, "QBI_BASE_URL", "https://api.example")
    monkeypatch.setitem(flask_app.config, "QBI_TOKEN", "token-de-prueba")
    monkeypatch.setitem(flask_app.config, "QBI_CLIENT_ID", "554")


@pytest.fixture(autouse=True)
def sin_smtp(monkeypatch):
    """Evita que los tests salgan a la red por SMTP.

    El envio del mail es sincrono dentro del request: sin este mock, cada
    emision exitosa esperaba el timeout del servidor de correo (~1s por test).
    Eso mismo le pasa a un usuario real si el SMTP esta lento.
    """
    enviados = []
    monkeypatch.setattr(
        recetas_routes,
        "_enviar_email_receta",
        lambda *a, **kw: enviados.append(a),
    )
    return enviados


def _login(client, rol="profesional"):
    login_as(client, MockUser(user_id=1, rol=rol))


def _db(monkeypatch, filas=None):
    """El modulo hace dos SELECT: paciente y usuario."""
    return make_db(
        monkeypatch,
        recetas_routes,
        fetchone_results=filas if filas is not None else [PACIENTE, USUARIO],
    )


def _emitir(client, monkeypatch, cuerpo, respuesta=RESPUESTA_QBI):
    enviados = []

    def _fake(payload):
        enviados.append(payload)
        return respuesta

    monkeypatch.setattr(qbi_client, "emitir_receta", _fake)
    monkeypatch.setattr(recetas_routes.qbi_client, "emitir_receta", _fake)
    return client.post("/api/recetas/emitir", json=cuerpo), enviados


# --------------------------------------------------------- configuracion


def test_sin_configurar_devuelve_503(client, monkeypatch):
    _login(client)
    monkeypatch.setitem(flask_app.config, "QBI_BASE_URL", "")

    respuesta = client.post("/api/recetas/emitir", json={"paciente_id": 4})

    assert respuesta.status_code == 503


def test_config_reporta_no_configurado(client, monkeypatch):
    _login(client)
    monkeypatch.setitem(flask_app.config, "QBI_BASE_URL", "")

    respuesta = client.get("/api/recetas/config")

    assert respuesta.status_code == 503
    assert respuesta.get_json()["configured"] is False


def test_no_hay_url_por_defecto():
    """El default apuntaba a homologación: emitía recetas de prueba en producción."""
    from app.config import Config

    assert not Config.QBI_BASE_URL or "hml" not in Config.QBI_BASE_URL


# --------------------------------------------------------- reglas de negocio


def test_rechaza_mas_de_tres_medicamentos(client, monkeypatch, configurado):
    _login(client)
    _db(monkeypatch)
    meds = [{"regNo": f"R{i}", "cantidad": 1} for i in range(4)]

    respuesta, enviados = _emitir(
        client, monkeypatch, {"paciente_id": 4, "medicamentos": meds}
    )

    assert respuesta.status_code == 400
    assert "3 medicamentos" in respuesta.get_json()["error"]
    assert enviados == []  # no se llamó al proveedor


def test_acepta_exactamente_tres_medicamentos(client, monkeypatch, configurado):
    _login(client)
    _db(monkeypatch)
    meds = [{"regNo": f"R{i}", "cantidad": 1} for i in range(3)]

    respuesta, enviados = _emitir(
        client, monkeypatch, {"paciente_id": 4, "medicamentos": meds}
    )

    assert respuesta.status_code == 200
    assert len(enviados) == 1


@pytest.mark.parametrize("cantidad", [0, 3, 10])
def test_rechaza_cantidad_fuera_de_rango(client, monkeypatch, configurado, cantidad):
    _login(client)
    _db(monkeypatch)

    respuesta, enviados = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": cantidad}]},
    )

    assert respuesta.status_code == 400
    assert "entre 1 y 2" in respuesta.get_json()["error"]
    assert enviados == []


def test_rechaza_receta_sin_medicamentos(client, monkeypatch, configurado):
    _login(client)
    _db(monkeypatch)

    respuesta, _ = _emitir(client, monkeypatch, {"paciente_id": 4, "medicamentos": []})

    assert respuesta.status_code == 400


def test_diagnostico_por_defecto_es_z769(client, monkeypatch, configurado):
    _login(client)
    _db(monkeypatch)

    _, enviados = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert enviados[0]["codigoDiagnostico"] == "Z769"
    assert enviados[0]["observaciones"] == "Tratamiento prolongado"


def test_el_diagnostico_explicito_gana(client, monkeypatch, configurado):
    _login(client)
    _db(monkeypatch)

    _, enviados = _emitir(
        client,
        monkeypatch,
        {
            "paciente_id": 4,
            "medicamentos": [{"regNo": "R1", "cantidad": 1}],
            "codigoDiagnostico": "J189",
            "diagnostico": "Neumonía",
        },
    )

    assert enviados[0]["codigoDiagnostico"] == "J189"


# --------------------------------------------------------- datos del profesional


def test_el_lugar_de_atencion_sale_del_profesional(client, monkeypatch, configurado):
    """Antes era una constante en el código, duplicada además en el frontend."""
    _login(client)
    _db(monkeypatch)

    _, enviados = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    lugar = enviados[0]["lugarAtencion"]
    assert lugar["nombreConsultorio"] == "Consultorio Central"
    assert lugar["domicilio"]["direccion"] == "Av. Siempreviva 742"
    assert lugar["email"] == "consultorio@cau.example"


def test_el_medico_sale_del_usuario_logueado(client, monkeypatch, configurado):
    _login(client)
    _db(monkeypatch)

    _, enviados = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    medico = enviados[0]["medico"]
    assert medico["nroDoc"] == "20111222"
    assert medico["matricula"]["numero"] == "12345"


def test_sin_matricula_no_se_emite(client, monkeypatch, configurado):
    _login(client)
    sin_matricula = dict(USUARIO, matricula_numero=None)
    _db(monkeypatch, filas=[PACIENTE, sin_matricula])

    respuesta, enviados = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert respuesta.status_code == 400
    assert "matrícula" in respuesta.get_json()["error"].lower()
    assert enviados == []


def test_sin_lugar_de_atencion_no_se_emite(client, monkeypatch, configurado):
    _login(client)
    sin_lugar = dict(USUARIO, lugar_atencion_direccion=None)
    _db(monkeypatch, filas=[PACIENTE, sin_lugar])

    respuesta, enviados = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert respuesta.status_code == 400
    assert enviados == []


# --------------------------------------------------------- persistencia


def test_emitir_guarda_la_receta_y_registra_la_evolucion(client, monkeypatch, configurado):
    """Una receta es un acto médico: tiene que quedar en la historia clínica."""
    _login(client)
    _, cursor = _db(monkeypatch)

    _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert any("INSERT INTO recetas_electronicas" in q for q in cursor.queries)
    assert any("INSERT INTO evoluciones" in q for q in cursor.queries)


def test_el_paciente_inexistente_devuelve_404(client, monkeypatch, configurado):
    _login(client)
    _db(monkeypatch, filas=[None])

    respuesta, enviados = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 999, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert respuesta.status_code == 404
    assert enviados == []


# --------------------------------------------------------- estudios


def test_un_estudio_por_llamada(client, monkeypatch, configurado):
    """Cada bloque de texto libre es una prescripción independiente."""
    _login(client)
    _db(monkeypatch, filas=[PACIENTE, USUARIO, PACIENTE, USUARIO])

    enviados = []
    monkeypatch.setattr(
        recetas_routes.qbi_client,
        "emitir_practica",
        lambda payload: enviados.append(payload) or RESPUESTA_QBI,
    )

    respuesta = client.post(
        "/api/recetas/emitir",
        json={
            "paciente_id": 4,
            "tipo": "estudio",
            "estudios": [{"texto": "Hemograma"}, {"texto": "Radiografía de tórax"}],
        },
    )

    assert respuesta.status_code == 200
    assert len(enviados) == 2
    assert enviados[0]["prescripcion"][0]["nombre"] == "Hemograma"
    assert enviados[1]["prescripcion"][0]["nombre"] == "Radiografía de tórax"


def test_estudio_sin_texto_se_rechaza(client, monkeypatch, configurado):
    _login(client)
    _db(monkeypatch)

    respuesta = client.post(
        "/api/recetas/emitir",
        json={"paciente_id": 4, "tipo": "estudio", "estudios": [{"texto": "  "}]},
    )

    assert respuesta.status_code == 400


def test_tipo_invalido_se_rechaza(client, monkeypatch, configurado):
    _login(client)
    _db(monkeypatch)

    respuesta = client.post(
        "/api/recetas/emitir", json={"paciente_id": 4, "tipo": "otra_cosa"}
    )

    assert respuesta.status_code == 400


# --------------------------------------------------------- permisos


def test_emitir_requiere_login(client):
    assert client.post("/api/recetas/emitir", json={}).status_code == 401


def test_administrativo_no_puede_emitir(client, monkeypatch, configurado):
    _login(client, rol="administrativo")
    _db(monkeypatch)

    assert client.post("/api/recetas/emitir", json={"paciente_id": 4}).status_code == 403


def test_anular_requiere_rol(client, monkeypatch, configurado):
    _login(client, rol="administrativo")
    _db(monkeypatch)

    assert client.delete("/api/recetas/anular/REC-1").status_code == 403


def test_anular_marca_la_receta_local(client, monkeypatch, configurado):
    _login(client)
    _, cursor = _db(monkeypatch)
    monkeypatch.setattr(recetas_routes.qbi_client, "anular_receta", lambda h: {"ok": True})

    respuesta = client.delete("/api/recetas/anular/REC-1")

    assert respuesta.status_code == 200
    assert any("estado = 'anulada'" in q for q in cursor.queries)


# --------------------------------------------------------- mail


def test_emitir_manda_el_mail_si_hay_direccion(client, monkeypatch, configurado, sin_smtp):
    _login(client)
    _db(monkeypatch)

    _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert len(sin_smtp) == 1
    email, _nombre, link, _detalle = sin_smtp[0]
    assert email == "ana@example.com"
    assert link == "https://s3/receta.pdf"


def test_un_fallo_del_mail_no_invalida_la_receta(client, monkeypatch, configurado):
    """La receta ya se emitió en el proveedor: no se puede fallar el request por el mail."""
    _login(client)
    _db(monkeypatch)
    monkeypatch.setattr(
        recetas_routes,
        "_enviar_email_receta",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("smtp caido")),
    )

    respuesta, _ = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["receta_hash"] == "REC-1"


def test_sin_email_no_intenta_mandar(client, monkeypatch, configurado, sin_smtp):
    _login(client)
    _db(monkeypatch, filas=[dict(PACIENTE, email=None), USUARIO])

    _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert sin_smtp == []


# --------------------------------------------------------- datos del paciente


def test_sin_domicilio_del_paciente_avisa_antes_de_llamar_al_proveedor(client, monkeypatch, configurado):
    """El proveedor rechaza con QBI240 'debe ingresar calle y numero', que no
    dice de quien es el domicilio ni donde se carga."""
    _login(client)
    sin_direccion = dict(PACIENTE)
    sin_direccion.pop("direccion")
    _db(monkeypatch, filas=[sin_direccion, USUARIO])

    respuesta, enviados = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert respuesta.status_code == 400
    assert "domicilio del paciente" in respuesta.get_json()["error"]
    assert enviados == []


def test_sin_dni_del_paciente_tambien_avisa(client, monkeypatch, configurado):
    _login(client)
    sin_dni = dict(PACIENTE, dni=None)
    _db(monkeypatch, filas=[sin_dni, USUARIO])

    respuesta, enviados = _emitir(
        client,
        monkeypatch,
        {"paciente_id": 4, "medicamentos": [{"regNo": "R1", "cantidad": 1}]},
    )

    assert respuesta.status_code == 400
    assert "DNI del paciente" in respuesta.get_json()["error"]
    assert enviados == []
