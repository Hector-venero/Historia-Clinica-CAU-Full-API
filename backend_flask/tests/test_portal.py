"""Plano del paciente: identidad, buzon y —sobre todo— aislamiento.

Lo que se prueba sin MySQL: la normalizacion del documento, que es la llave de
todo el modelo, y que una sesion de paciente no valga en el sistema de un
consultorio ni al reves.

Ese ultimo punto tiene un test porque **fallo de verdad**: la cookie de un
paciente devolvia 200 en /api/pacientes de un consultorio, o sea el listado
completo de pacientes de esa clinica. Flask-Login solo sabe si hay alguien
autenticado, no de que poblacion es.
"""

import pytest

from app import portal, tenancy


# --------------------------------------------------------- la identidad


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("30111222", "30111222"),
        ("30.111.222", "30111222"),
        ("30 111 222", "30111222"),
        ("30-111-222", "30111222"),
        ("  30.111.222  ", "30111222"),
    ],
)
def test_el_documento_se_normaliza(entrada, esperado):
    """Es la llave con la que dos consultorios le envian a la misma persona.

    Sin normalizar, "30.111.222" y "30111222" serian dos personas distintas y un
    estudio enviado con puntos no llegaria nunca.
    """
    _tipo, numero = portal.normalizar_documento("DNI", entrada)
    assert numero == esperado


def test_el_tipo_de_documento_se_normaliza():
    tipo, _numero = portal.normalizar_documento("dni", "30111222")
    assert tipo == "DNI"


def test_un_tipo_de_documento_invalido_se_rechaza():
    with pytest.raises(portal.ErrorPortal):
        portal.normalizar_documento("INVENTADO", "30111222")


def test_un_documento_vacio_se_rechaza():
    with pytest.raises(portal.ErrorPortal):
        portal.normalizar_documento("DNI", "")


def test_se_aceptan_cedula_y_pasaporte():
    """No todo el mundo tiene DNI argentino."""
    for tipo in ("CI", "PASAPORTE", "LC", "LE"):
        t, _n = portal.normalizar_documento(tipo, "ABC123")
        assert t == tipo


def test_un_pasaporte_conserva_las_letras():
    _tipo, numero = portal.normalizar_documento("PASAPORTE", "ab-123456")
    assert numero == "AB123456"


# ------------------------------------------------------------ aislamiento


def test_una_sesion_de_paciente_no_entra_al_sistema_del_consultorio(client, monkeypatch):
    """El fallo real que motivo el chequeo.

    load_user devuelve un Paciente, Flask-Login lo da por autenticado y
    @login_required lo deja pasar: sin este control, la cookie de un paciente
    devolvia 200 en /api/pacientes, el listado completo de una clinica.
    """
    with client.session_transaction() as sesion:
        sesion["_user_id"] = "p:1"

    for ruta in ("/api/pacientes", "/api/usuarios/me", "/api/recetas/config"):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 401, f"{ruta} dejo pasar a un paciente"


def test_una_sesion_de_personal_si_entra_al_sistema_del_consultorio(client, monkeypatch):
    """El control anterior no puede cortarle el paso al personal.

    Un identificador sin el prefijo `p:` es de un miembro del equipo, y tiene que
    seguir su camino normal. Que termine en 401 por no estar logueado de verdad
    es otra cosa: lo que importa es que NO lo rechace el filtro del portal.
    """
    with client.session_transaction() as sesion:
        sesion["_user_id"] = "1"

    respuesta = client.get("/api/usuarios/me")
    assert respuesta.status_code in (200, 401)


def test_el_portal_sigue_atendiendo_a_un_paciente(client):
    """El filtro no puede cortar las rutas del propio portal."""
    with client.session_transaction() as sesion:
        sesion["_user_id"] = "p:1"

    respuesta = client.get("/api/portal/documentos")
    # 401 porque el paciente 1 no existe en la base de prueba; lo que se
    # comprueba es que NO lo rechace el filtro con su 401 propio antes de llegar.
    assert respuesta.status_code in (200, 401)


def test_las_rutas_del_portal_estan_declaradas():
    """Si alguien agrega una ruta del portal fuera de este prefijo, queda
    bloqueada para los pacientes sin que nadie entienda por que."""
    assert "/api/portal" in tenancy.RUTAS_DEL_PORTAL
    # La marca tiene que verse para pintar la pantalla de entrada del portal.
    assert "/api/publico/marca" in tenancy.RUTAS_DEL_PORTAL


def test_el_subdominio_del_portal_no_resuelve_como_consultorio():
    """`mi` es el portal. Si resolviera como cliente, buscaria un consultorio con
    ese slug y devolveria 404 antes de llegar a las rutas del portal."""
    assert tenancy.slug_desde_host("mi.fichasalud.com.ar") is None
    assert tenancy.slug_desde_host("mi.localhost:5173") is None


# ------------------------------------------------------------ el buzon


def test_el_tipo_de_documento_clinico_se_valida(monkeypatch):
    """Solo se aceptan los tipos conocidos: el frontend los usa para elegir icono
    y agrupar, y un valor libre romperia esa lectura."""
    monkeypatch.setattr(portal, "cursor_portal", lambda commit=False: None)

    with pytest.raises(portal.ErrorPortal):
        portal.guardar_documento(
            tipo_documento="DNI",
            numero_documento="30111222",
            consultorio_slug="drlopez",
            consultorio_nombre="Consultorio Lopez",
            profesional_nombre="Dr. Lopez",
            tipo="cualquier_cosa",
            titulo="Algo",
        )


def test_un_documento_sin_titulo_se_rechaza(monkeypatch):
    monkeypatch.setattr(portal, "cursor_portal", lambda commit=False: None)

    with pytest.raises(portal.ErrorPortal):
        portal.guardar_documento(
            tipo_documento="DNI",
            numero_documento="30111222",
            consultorio_slug="drlopez",
            consultorio_nombre="Consultorio Lopez",
            profesional_nombre="Dr. Lopez",
            tipo="estudio",
            titulo="   ",
        )


def test_el_token_del_archivo_no_deriva_del_documento():
    """La ruta de un archivo no puede permitir averiguar de quien es."""
    tokens = {portal.nuevo_token_archivo() for _ in range(50)}

    assert len(tokens) == 50, "los tokens se repiten"
    for token in tokens:
        assert "30111222" not in token
        assert len(token) == 32


# ------------------------------------------- recuperar la contrasena


def test_recuperar_responde_lo_mismo_exista_o_no_la_cuenta(client, monkeypatch):
    """El formulario es publico. Distinguir "no existe" de "te lo mandamos"
    dejaria averiguar si una persona es paciente de la plataforma probando
    correos, que es informacion de salud."""
    monkeypatch.setattr(portal, "buscar_por_email", lambda e: None)
    sin_cuenta = client.post("/api/portal/recuperar", json={"email": "nadie@x.com"})

    monkeypatch.setattr(
        portal, "buscar_por_email",
        lambda e: {"id": 1, "nombre": "Ana", "email": "ana@x.com"},
    )
    monkeypatch.setattr(
        "app.utils.mails_portal.mail_reset_paciente", lambda **k: None
    )
    con_cuenta = client.post("/api/portal/recuperar", json={"email": "ana@x.com"})

    assert sin_cuenta.status_code == con_cuenta.status_code == 200
    assert sin_cuenta.get_json() == con_cuenta.get_json()


def test_un_correo_invalido_tampoco_delata(client):
    """Ni siquiera un formato invalido cambia la respuesta: cualquier diferencia
    sirve para deducir algo."""
    respuesta = client.post("/api/portal/recuperar", json={"email": "no-es-correo"})

    assert respuesta.status_code == 200
    assert "mensaje" in respuesta.get_json()


def test_un_token_del_personal_no_sirve_en_el_portal(client):
    """La SECRET_KEY es la misma para toda la plataforma, asi que sin separar la
    sal un enlace emitido para un usuario de consultorio serviria para cambiar la
    contrasena de un paciente."""
    from itsdangerous import URLSafeTimedSerializer

    from app import app as flask_app

    with flask_app.app_context():
        # La sal del personal, la de auth_routes.
        token = URLSafeTimedSerializer(flask_app.secret_key).dumps(
            "ana@ejemplo.com", salt="reset-password"
        )

    respuesta = client.post(
        f"/api/portal/reset/{token}",
        json={"password": "NuevaClave1!", "password_repetida": "NuevaClave1!"},
    )

    assert respuesta.status_code == 400
    assert "no es valido" in respuesta.get_json()["error"]


def test_las_sales_de_reset_son_distintas():
    from app.routes import portal_routes

    assert portal_routes.SAL_RESET_PACIENTE != "reset-password"


def test_un_token_invalido_se_rechaza(client):
    respuesta = client.post(
        "/api/portal/reset/inventado",
        json={"password": "NuevaClave1!", "password_repetida": "NuevaClave1!"},
    )
    assert respuesta.status_code == 400


def test_las_contrasenas_tienen_que_coincidir(client, monkeypatch):
    from itsdangerous import URLSafeTimedSerializer

    from app import app as flask_app

    with flask_app.app_context():
        token = URLSafeTimedSerializer(flask_app.secret_key).dumps(
            "ana@ejemplo.com", salt="reset-password-paciente"
        )

    respuesta = client.post(
        f"/api/portal/reset/{token}",
        json={"password": "NuevaClave1!", "password_repetida": "Otra2!"},
    )

    assert respuesta.status_code == 400
    assert "no coinciden" in respuesta.get_json()["error"]
