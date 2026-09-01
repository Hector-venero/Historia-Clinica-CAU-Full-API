from flask_login import UserMixin

from app.routes import auth_routes
from conftest import make_db


def sin_intentos_previos(monkeypatch):
    """Base falsa para el contador de intentos fallidos.

    El login ahora toca la base ANTES de mirar al usuario: cuenta los intentos
    fallidos para frenar la fuerza bruta. Sin esta base falsa, cada test se
    queda intentando conectarse a MySQL de verdad — la suite entera paso de
    0,7 s a 120 s la primera vez que se engancho el freno.

    `fetchone` devolviendo None es "esta cuenta no tiene fallos anotados", que
    es el estado normal.
    """
    return make_db(monkeypatch, auth_routes, fetchone_results=[None, None])


class StubAuthUser(UserMixin):
    def __init__(self, activo=True):
        self.id = 1
        self.nombre = "Alice"
        self.apellido = "Ejemplo"
        self.username = "alice"
        self.email = "alice@example.com"
        self.rol = "director"
        self.activo = activo

    def verificar_password(self, raw_password):
        return raw_password == "secret123"


def test_login_rejects_missing_credentials(client):
    response = client.post("/api/login", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_login_success(client, monkeypatch):
    sin_intentos_previos(monkeypatch)
    stub_user = StubAuthUser()

    monkeypatch.setattr(
        auth_routes.Usuario,
        "obtener_por_username",
        staticmethod(lambda username: stub_user if username == "alice" else None),
    )

    response = client.post(
        "/api/login",
        json={"username": "alice", "password": "secret123"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["user"]["username"] == "alice"
    assert payload["user"]["rol"] == "director"

    with client.session_transaction() as session:
        assert session.get("_user_id") == "1"


def test_login_rejects_wrong_password(client, monkeypatch):
    sin_intentos_previos(monkeypatch)
    stub_user = StubAuthUser()

    monkeypatch.setattr(
        auth_routes.Usuario,
        "obtener_por_username",
        staticmethod(lambda username: stub_user if username == "alice" else None),
    )

    response = client.post(
        "/api/login",
        json={"username": "alice", "password": "equivocada"},
    )

    assert response.status_code == 401
    with client.session_transaction() as session:
        assert session.get("_user_id") is None


def test_login_rejects_unknown_user(client, monkeypatch):
    sin_intentos_previos(monkeypatch)
    monkeypatch.setattr(
        auth_routes.Usuario,
        "obtener_por_username",
        staticmethod(lambda username: None),
    )

    response = client.post(
        "/api/login",
        json={"username": "nadie", "password": "secret123"},
    )

    assert response.status_code == 401


def test_login_rejects_inactive_user(client, monkeypatch):
    sin_intentos_previos(monkeypatch)
    """Un usuario dado de baja no se puede loguear.

    obtener_por_username filtra por activo = 1, asi que un usuario inactivo es
    indistinguible de uno inexistente. Sin ese filtro, dar de baja a alguien no
    le impedia seguir entrando.
    """
    usuarios = {}  # ningun usuario activo: el inactivo no aparece

    monkeypatch.setattr(
        auth_routes.Usuario,
        "obtener_por_username",
        staticmethod(lambda username: usuarios.get(username)),
    )

    response = client.post(
        "/api/login",
        json={"username": "alice", "password": "secret123"},
    )

    assert response.status_code == 401
    with client.session_transaction() as session:
        assert session.get("_user_id") is None


# ------------------------------------------------- el freno, desde el endpoint


def test_el_login_devuelve_429_cuando_hay_que_esperar(client, monkeypatch):
    """429 y no 401: es una respuesta distinta y quien la lea tiene que poder
    distinguirla, empezando por el propio frontend."""
    from app import antifuerzabruta

    monkeypatch.setattr(
        antifuerzabruta, "revisar",
        lambda *a, **k: (_ for _ in ()).throw(antifuerzabruta.DemasiadosIntentos(120)),
    )

    r = client.post("/api/login", json={"username": "alice", "password": "loquesea"})

    assert r.status_code == 429
    # El mensaje dice cuanto falta: "demasiados intentos" a secas hace recargar
    # cada dos segundos, que es lo que se esta tratando de evitar.
    assert "2 minutos" in r.get_json()["error"]


def test_el_login_no_consulta_al_usuario_si_hay_que_esperar(client, monkeypatch):
    """El punto del freno es no hacer el trabajo, no hacerlo y descartarlo."""
    from app import antifuerzabruta

    consultas = []
    monkeypatch.setattr(
        auth_routes.Usuario, "obtener_por_username",
        staticmethod(lambda username: consultas.append(username)),
    )
    monkeypatch.setattr(
        antifuerzabruta, "revisar",
        lambda *a, **k: (_ for _ in ()).throw(antifuerzabruta.DemasiadosIntentos(60)),
    )

    client.post("/api/login", json={"username": "alice", "password": "x"})

    assert consultas == []


def test_una_clave_equivocada_queda_anotada(client, monkeypatch):
    sin_intentos_previos(monkeypatch)
    monkeypatch.setattr(
        auth_routes.Usuario, "obtener_por_username", staticmethod(lambda username: None)
    )

    anotados = []
    from app import antifuerzabruta

    monkeypatch.setattr(
        antifuerzabruta, "registrar_fallo",
        lambda _cur, usuario, ip, **k: anotados.append((usuario, ip)),
    )

    r = client.post("/api/login", json={"username": "alice", "password": "mala"})

    assert r.status_code == 401
    assert anotados == [("alice", "127.0.0.1")]


def test_entrar_bien_limpia_el_contador(client, monkeypatch):
    sin_intentos_previos(monkeypatch)
    stub_user = StubAuthUser()
    monkeypatch.setattr(
        auth_routes.Usuario, "obtener_por_username",
        staticmethod(lambda username: stub_user if username == "alice" else None),
    )

    limpiados = []
    from app import antifuerzabruta

    monkeypatch.setattr(
        antifuerzabruta, "limpiar", lambda _cur, usuario, ip: limpiados.append(usuario)
    )

    r = client.post("/api/login", json={"username": "alice", "password": "secret123"})

    assert r.status_code == 200
    assert limpiados == ["alice"]
