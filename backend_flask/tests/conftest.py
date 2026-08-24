"""Fixtures compartidas de los tests del backend.

No hace falta MySQL: la DB se reemplaza por dobles en memoria. Cada test
declara que filas devuelve el cursor y, si quiere, en que llamada a execute()
debe fallar, para poder testear rollback y cierre de conexion.

Adaptado del harness del fork, con un agregado: aca las rutas usan el context
manager db_cursor() en vez de get_connection() suelto, asi que se provee
patch_db_cursor() ademas de patch_get_connection().
"""

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from flask_login import UserMixin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app as flask_app  # noqa: E402
from app import login_manager  # noqa: E402


class MockUser(UserMixin):
    """Usuario de sesion. Trae los campos profesionales que usa el modulo de recetas."""

    def __init__(
        self,
        user_id,
        rol,
        nombre="Test User",
        username="test",
        email="test@example.com",
        **extra,
    ):
        self.id = user_id
        self.rol = rol
        self.nombre = nombre
        self.username = username
        self.email = email
        self.duracion_turno = 30
        self.foto = None
        # Campos de matricula profesional; se pisan por kwargs cuando el test los necesita.
        self.apellido = extra.pop("apellido", "Apellido")
        self.dni = extra.pop("dni", "12345678")
        self.sexo = extra.pop("sexo", "M")
        self.profesion = extra.pop("profesion", "Medico")
        self.matricula_tipo = extra.pop("matricula_tipo", "MN")
        self.matricula_numero = extra.pop("matricula_numero", "12345")
        self.matricula_provincia = extra.pop("matricula_provincia", "Buenos Aires")
        for clave, valor in extra.items():
            setattr(self, clave, valor)


class FakeCursor:
    def __init__(
        self,
        fetchone_results=None,
        fetchall_results=None,
        lastrowid=1,
        execute_side_effects=None,
    ):
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.lastrowid = lastrowid
        self.executed = []
        self.closed = False
        # Excepciones a levantar en llamadas sucesivas a execute(), por posicion.
        # None en una posicion = ese execute() se comporta normal.
        self._execute_side_effects = list(execute_side_effects or [])

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if self._execute_side_effects:
            efecto = self._execute_side_effects.pop(0)
            if efecto is not None:
                raise efecto

    def fetchone(self):
        if self._fetchone_results:
            return self._fetchone_results.pop(0)
        return None

    def fetchall(self):
        if self._fetchall_results:
            return self._fetchall_results.pop(0)
        return []

    def close(self):
        self.closed = True

    @property
    def queries(self):
        """Solo el texto de las queries, para asertar sin repetir los params."""
        return [q for q, _ in self.executed]


class FakeConnection:
    def __init__(self, cursor, connection_id=1234):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.connection_id = connection_id

    def cursor(self, dictionary=False, buffered=False):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def patch_get_connection(monkeypatch, modulo, conexion):
    """Para rutas que todavia hacen get_connection() a mano."""
    monkeypatch.setattr(modulo, "get_connection", lambda *a, **kw: conexion)
    return conexion


def patch_db_cursor(monkeypatch, modulo, conexion):
    """Para rutas que usan el context manager db_cursor().

    Replica su contrato: cierra el cursor y la conexion pase lo que pase, para
    que un test pueda verificar que una excepcion no filtra la conexion.
    """

    @contextmanager
    def _fake_db_cursor(dictionary=True, commit=False):
        cursor = conexion.cursor(dictionary=dictionary)
        try:
            yield conexion, cursor
            if commit:
                conexion.commit()
        except Exception:
            if commit:
                conexion.rollback()
            raise
        finally:
            cursor.close()
            conexion.close()

    monkeypatch.setattr(modulo, "db_cursor", _fake_db_cursor)
    return conexion


def make_db(monkeypatch, modulo, **kwargs):
    """Atajo: arma cursor + conexion falsos y los engancha al modulo.

    Devuelve (conexion, cursor) para poder asertar sobre commit/rollback/closed
    y sobre las queries ejecutadas.
    """
    cursor = FakeCursor(**kwargs)
    conexion = FakeConnection(cursor)
    if hasattr(modulo, "db_cursor"):
        patch_db_cursor(monkeypatch, modulo, conexion)
    if hasattr(modulo, "get_connection"):
        patch_get_connection(monkeypatch, modulo, conexion)
    return conexion, cursor


def login_as(client, user):
    client.test_users[str(user.id)] = user
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True


@pytest.fixture
def client(monkeypatch):
    test_users = {}

    monkeypatch.setattr(
        login_manager, "_user_callback", lambda user_id: test_users.get(str(user_id))
    )
    flask_app.config.update(TESTING=True)

    with flask_app.test_client() as test_client:
        test_client.test_users = test_users
        yield test_client
