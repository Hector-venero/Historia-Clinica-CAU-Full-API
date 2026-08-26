"""Acceso al plano de control: que consultorios existen y donde vive cada uno.

Es la unica parte del sistema que habla con la base `plataforma`. Deliberadamente
no usa `database.get_connection()`: esa funcion resuelve la base **del cliente
actual**, y mezclarlas seria el camino corto a que un pedido de un consultorio
termine leyendo el plano de control, o peor, al reves.

Aca no hay datos clinicos. Solo el catalogo de clientes y su configuracion.
"""

import os

from contextlib import contextmanager

import mysql.connector

from app.utils.secretos import descifrar

ESTADOS = ("prueba", "activo", "suspendido", "cancelado")

# Estados en los que el consultorio puede usar el sistema. `suspendido` y
# `cancelado` conservan los datos —son del paciente, no del proveedor— pero no
# dejan entrar.
ESTADOS_ACTIVOS = ("prueba", "activo")


def _config():
    """Conexion al plano de control.

    Credenciales propias, distintas de las del inquilino: el usuario que lee el
    catalogo de clientes no tiene por que poder tocar una base clinica.
    """
    # `or` y no un default de os.getenv: docker compose pasa las variables no
    # definidas como cadena vacia, no como ausentes, y os.getenv solo aplica el
    # default cuando la variable no existe. Ver la nota en migrate.py.
    return {
        "host": os.getenv("PLATAFORMA_DB_HOST") or os.getenv("DB_HOST") or "db",
        "port": int(os.getenv("PLATAFORMA_DB_PORT") or os.getenv("DB_PORT") or "3306"),
        "user": os.getenv("PLATAFORMA_DB_USER") or "root",
        "password": os.getenv("PLATAFORMA_DB_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD") or "",
        "database": os.getenv("PLATAFORMA_DB_NAME") or "plataforma",
    }


@contextmanager
def cursor_plataforma(commit=False):
    """Mismo contrato que `database.db_cursor()`, contra el plano de control."""
    conn = mysql.connector.connect(**_config())
    cur = conn.cursor(dictionary=True)
    try:
        yield conn, cur
        if commit:
            conn.commit()
    except Exception:
        if commit:
            try:
                conn.rollback()
            except mysql.connector.Error:
                pass
        raise
    finally:
        try:
            cur.close()
        except mysql.connector.Error:
            pass
        conn.close()


class Cliente:
    """Un consultorio. Lo que hace falta para atender un pedido suyo."""

    def __init__(self, fila):
        self.id = fila["id"]
        self.slug = fila["slug"]
        self.nombre = fila["nombre"]
        self.estado = fila["estado"]
        self.plan = fila["plan"]
        self.prueba_hasta = fila.get("prueba_hasta")
        self.db_nombre = fila["db_nombre"]
        self.db_usuario = fila["db_usuario"]
        self._db_password = fila["db_password"]

    @property
    def db_password(self):
        """Se descifra al usarla, no al cargar el cliente.

        El cliente se cachea en memoria; la contrasena en claro no.
        """
        return descifrar(self._db_password)

    @property
    def activo(self):
        return self.estado in ESTADOS_ACTIVOS

    def config_db(self):
        """Parametros de conexion a la base de ESTE consultorio."""
        return {
            "host": os.getenv("DB_HOST", "db"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": self.db_usuario,
            "password": self.db_password,
            "database": self.db_nombre,
        }

    def __repr__(self):
        return f"<Cliente {self.slug} ({self.estado})>"


def buscar_por_slug(slug):
    """Devuelve el Cliente o None. No distingue 'no existe' de 'cancelado':
    eso lo decide quien llama, que es el que sabe que mensaje corresponde."""
    if not slug:
        return None
    with cursor_plataforma() as (_conn, cur):
        cur.execute("SELECT * FROM clientes WHERE slug = %s", (slug,))
        fila = cur.fetchone()
    return Cliente(fila) if fila else None


def listar(estados=None):
    """Clientes, opcionalmente filtrados por estado. Lo usan las migraciones
    multi-inquilino y el panel."""
    with cursor_plataforma() as (_conn, cur):
        if estados:
            marcas = ", ".join(["%s"] * len(estados))
            cur.execute(
                f"SELECT * FROM clientes WHERE estado IN ({marcas}) ORDER BY slug",
                tuple(estados),
            )
        else:
            cur.execute("SELECT * FROM clientes ORDER BY slug")
        filas = cur.fetchall()
    return [Cliente(f) for f in filas]


def slug_disponible(slug):
    """Un slug esta libre si no lo tiene otro cliente y no esta reservado."""
    with cursor_plataforma() as (_conn, cur):
        cur.execute("SELECT 1 FROM slugs_reservados WHERE slug = %s", (slug,))
        if cur.fetchone():
            return False
        cur.execute("SELECT 1 FROM clientes WHERE slug = %s", (slug,))
        return cur.fetchone() is None


def config_de(cliente_id):
    """Configuracion del cliente: marca, modulos, credenciales de recetas."""
    with cursor_plataforma() as (_conn, cur):
        cur.execute("SELECT * FROM clientes_config WHERE cliente_id = %s", (cliente_id,))
        return cur.fetchone()
