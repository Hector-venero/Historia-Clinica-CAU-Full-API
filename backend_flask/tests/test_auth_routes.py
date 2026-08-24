from flask_login import UserMixin

from app.routes import auth_routes


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
