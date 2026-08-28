"""Alta de un consultorio: crea su base, su usuario de MySQL y su admin.

Se ejecuta a mano mientras no exista el registro autoservicio (F6), y despues es
lo que ese registro va a invocar. Por eso la logica vive en `dar_de_alta()` y no
mezclada con el manejo de argumentos: cuando llegue la pantalla publica, la va a
llamar igual.

    python -m app.alta_cliente <slug> "<nombre>" <email> [--plan basico]

Es **idempotente hasta donde puede serlo**: si el slug ya existe, no hace nada y
avisa. Si falla a mitad de camino, deshace lo que alcanzo a crear en lugar de
dejar una base huerfana sin fila en el plano de control.
"""

import argparse
import os
import re
import secrets
import string
import subprocess
import sys

import mysql.connector
from werkzeug.security import generate_password_hash

from app import plataforma
from app.utils.secretos import cifrar

# Un slug tiene que poder ser una etiqueta DNS: minusculas, digitos y guiones,
# sin empezar ni terminar con guion, hasta 63 caracteres. Se valida aca y no solo
# en el formulario porque de esto depende que el subdominio exista.
#
# El cuantificador va en {0,61} y no en {1,61}: con el minimo en 1, el grupo
# opcional exigia dos caracteres despues del primero, de modo que 'a' se aceptaba
# y 'ab' se rechazaba.
PATRON_SLUG = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")

# DNS admite un solo caracter, pero un subdominio de una o dos letras no sirve
# como nombre de un consultorio y deja el espacio corto expuesto a que alguien lo
# tome sin usarlo.
LARGO_MINIMO_SLUG = 3

DIAS_DE_PRUEBA = int(os.getenv("DIAS_DE_PRUEBA", "30"))


class AltaInvalida(ValueError):
    """El pedido de alta no se puede atender (slug malo, ocupado, etc.)."""


def _conexion_admin():
    """Conexion con permisos para CREATE DATABASE y CREATE USER.

    No son las credenciales de la aplicacion: el usuario de la app tiene solo
    DML. Se reutilizan las de migracion, que ya existen para lo mismo.
    """
    return mysql.connector.connect(
        host=os.getenv("DB_HOST") or "db",
        port=int(os.getenv("DB_PORT") or "3306"),
        user=_usuario_admin(),
        password=_password_admin(),
    )


# `or` y no un default de os.getenv: docker compose pasa las variables no
# definidas como cadena vacia, no como ausentes, y os.getenv solo aplica el
# default cuando la variable no existe. Con "" se intentaba conectar sin
# contrasena y MySQL respondia 1045. Es la misma nota que ya trae migrate.py.
def _usuario_admin():
    return os.getenv("DB_MIGRATION_USER") or "root"


def _password_admin():
    return os.getenv("DB_MIGRATION_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD") or ""


def _password_aleatoria(largo=32):
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(largo))


def _nombres_mysql(slug):
    """Nombre de base y de usuario derivados del slug.

    El usuario de MySQL admite 32 caracteres; con el prefijo `c_` quedan 30 para
    el slug, asi que se recorta. La base tolera 64 y no necesita recorte.
    """
    limpio = slug.replace("-", "_")
    return f"hc_{limpio}", f"c_{limpio}"[:32]


def _validar(slug):
    if not PATRON_SLUG.match(slug or ""):
        raise AltaInvalida(
            f"'{slug}' no sirve como subdominio. Solo minusculas, numeros y "
            "guiones, sin empezar ni terminar con guion, hasta 63 caracteres."
        )
    if len(slug) < LARGO_MINIMO_SLUG:
        raise AltaInvalida(
            f"'{slug}' es demasiado corto: minimo {LARGO_MINIMO_SLUG} caracteres."
        )
    if not plataforma.slug_disponible(slug):
        raise AltaInvalida(f"El subdominio '{slug}' ya esta tomado o es reservado.")


def _crear_base_y_usuario(cur, db_nombre, db_usuario, db_password):
    # Los identificadores no se pueden parametrizar con %s, asi que van
    # interpolados. Es seguro porque salen de _nombres_mysql() sobre un slug ya
    # validado contra PATRON_SLUG: no puede contener comillas ni espacios.
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_nombre}` "
        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute(f"CREATE USER IF NOT EXISTS '{db_usuario}'@'%' IDENTIFIED BY %s", (db_password,))
    # Solo DML, y solo sobre SU base. Es lo que encierra una eventual inyeccion
    # SQL dentro de un consultorio en vez de exponer a todos.
    cur.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{db_nombre}`.* TO '{db_usuario}'@'%'"
    )
    cur.execute("FLUSH PRIVILEGES")


def _borrar_base_y_usuario(cur, db_nombre, db_usuario):
    cur.execute(f"DROP DATABASE IF EXISTS `{db_nombre}`")
    cur.execute(f"DROP USER IF EXISTS '{db_usuario}'@'%'")
    cur.execute("FLUSH PRIVILEGES")


# Sentencias de init.sql que no corresponden a la base de un cliente: crean la
# base del CAU, la seleccionan, o dan de alta usuarios de MySQL con permisos
# fijos sobre ella. El esquema del inquilino se arma con el resto.
PREFIJOS_ADMINISTRATIVOS = (
    "CREATE DATABASE",
    "USE ",
    "CREATE USER",
    "DROP USER",
    "GRANT",
    "REVOKE",
    "FLUSH",
    "SET ",
    # init.sql siembra un admin con la contrasena 'admin123', que esta publicada
    # en el README. Sirve para levantar el entorno de desarrollo, pero un
    # consultorio nuevo no puede nacer con una cuenta de credenciales conocidas.
    # El admin real lo crea _sembrar_admin() con una contrasena generada.
    "INSERT INTO USUARIOS",
)

# Fuera de /app: ese directorio es un bind mount del arbol de fuentes, y montar
# un archivo adentro deja el punto de montaje creado en el repositorio del host.
ESQUEMA_BASE = os.getenv("ESQUEMA_BASE") or "/esquema_base.sql"


def _es_administrativa(sentencia):
    limpia = sentencia.lstrip().upper()
    return limpia.startswith(PREFIJOS_ADMINISTRATIVOS)


def _crear_esquema_base(db_nombre, db_usuario, db_password):
    """Crea las tablas del sistema en la base recien creada.

    Las migraciones solo hacen ALTER, asi que sobre una base vacia fallan con
    1146 "Table doesn't exist": primero tiene que existir el esquema.

    Se lee de db/init.sql en lugar de mantener una copia para el inquilino,
    porque dos definiciones del mismo esquema divergen sin que nadie se entere
    —es exactamente lo que scripts/comparar_esquemas.sh existe para detectar—.
    Se descartan las sentencias administrativas y se ejecuta el resto dentro de
    la base del cliente.

    El tokenizador es el de migrate.py, que ya sabe de comillas, comentarios y
    apostrofes dentro de literales.
    """
    # Segun desde donde se lo invoque, migrate.py es un modulo suelto (corriendo
    # como script, con /app en sys.path) o parte del paquete (importado desde la
    # aplicacion, que es como llega el alta autoservicio). El alta por consola
    # funcionaba y la de la web fallaba con ModuleNotFoundError.
    try:
        from app.migrate import split_statements
    except ImportError:
        from migrate import split_statements

    if not os.path.exists(ESQUEMA_BASE):
        raise RuntimeError(
            f"No se encuentra el esquema base en {ESQUEMA_BASE}. "
            "Revisa el volumen de db/init.sql en docker-compose.yml."
        )

    with open(ESQUEMA_BASE, encoding="utf-8") as f:
        sql = f.read()

    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST") or "db",
        port=int(os.getenv("DB_PORT") or "3306"),
        user=_usuario_admin(),
        password=_password_admin(),
        database=db_nombre,
    )
    try:
        cur = conn.cursor()
        aplicadas = 0
        for sentencia in split_statements(sql):
            if _es_administrativa(sentencia):
                continue
            cur.execute(sentencia)
            aplicadas += 1
        conn.commit()
        cur.close()
        return aplicadas
    finally:
        conn.close()


def _migrar(db_nombre):
    """Corre las migraciones del inquilino contra su base recien creada.

    Se reutiliza migrate.py tal cual, apuntandolo con variables de entorno. Es
    el mismo mecanismo que usa scripts/comparar_esquemas.sh, asi que el esquema
    de un cliente nuevo es exactamente el que produce el arranque normal.
    """
    entorno = dict(os.environ)
    entorno["DB_NAME"] = db_nombre
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrate.py")

    resultado = subprocess.run(
        [sys.executable, ruta],
        env=entorno,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            "Fallaron las migraciones del cliente nuevo:\n"
            f"{resultado.stdout}\n{resultado.stderr}"
        )
    return resultado.stdout


def _sembrar_admin(db_nombre, db_usuario, db_password, nombre, email,
                   password_admin=None, password_hash=None):
    """Crea el primer usuario del consultorio, con rol director.

    Usa el mismo hash que el resto del sistema (scrypt via werkzeug), no bcrypt:
    si no, el usuario no podria iniciar sesion.

    Acepta el hash ya calculado para el alta autoservicio: ahi la contrasena se
    hashea al registrarse y entre eso y la creacion de la base puede pasar un
    dia, asi que no tiene por que existir en claro mientras tanto.
    """
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=db_usuario,
        password=db_password,
        database=db_nombre,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO usuarios (nombre, username, email, password_hash, rol, activo)
            VALUES (%s, %s, %s, %s, 'director', 1)
            """,
            (nombre, "admin", email,
             password_hash or generate_password_hash(password_admin, method="scrypt")),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


def dar_de_alta(slug, nombre, email, plan="basico", password_admin=None,
                password_hash=None, dias_prueba=None):
    """Deja el consultorio listo para entrar. Devuelve el resumen del alta.

    Es el unico camino de alta: lo usan el script de consola y el registro
    autoservicio. Dos caminos distintos terminarian divergiendo, y un dia se
    descubriria que los consultorios creados por la web no tienen algo que si
    tienen los otros.
    """
    _validar(slug)

    db_nombre, db_usuario = _nombres_mysql(slug)
    db_password = _password_aleatoria()
    # Con el hash ya calculado no hace falta inventar una contrasena: la eligio
    # quien se registro y solo el la conoce.
    if password_hash is None:
        password_admin = password_admin or _password_aleatoria(16)

    conn = _conexion_admin()
    cur = conn.cursor()
    creado = False

    try:
        _crear_base_y_usuario(cur, db_nombre, db_usuario, db_password)
        creado = True

        _crear_esquema_base(db_nombre, db_usuario, db_password)
        _migrar(db_nombre)
        _sembrar_admin(db_nombre, db_usuario, db_password, nombre, email,
                       password_admin, password_hash)

        with plataforma.cursor_plataforma(commit=True) as (_c, pcur):
            pcur.execute(
                """
                INSERT INTO clientes
                    (slug, nombre, email_contacto, estado, plan,
                     prueba_hasta, db_nombre, db_usuario, db_password)
                VALUES (%s, %s, %s, 'prueba', %s,
                        DATE_ADD(CURDATE(), INTERVAL %s DAY), %s, %s, %s)
                """,
                (slug, nombre, email, plan, dias_prueba or DIAS_DE_PRUEBA,
                 db_nombre, db_usuario, cifrar(db_password)),
            )
            cliente_id = pcur.lastrowid
            pcur.execute(
                "INSERT INTO clientes_config (cliente_id, nombre_visible) VALUES (%s, %s)",
                (cliente_id, nombre),
            )
    except Exception:
        # Sin esto queda una base creada sin fila en el plano de control: nadie
        # la ve, nadie la limpia, y el slug parece libre pero la base ya existe.
        if creado:
            try:
                _borrar_base_y_usuario(cur, db_nombre, db_usuario)
                conn.commit()
            except mysql.connector.Error:
                pass
        raise
    finally:
        cur.close()
        conn.close()

    return {
        "cliente_id": cliente_id,
        "slug": slug,
        "nombre": nombre,
        "db_nombre": db_nombre,
        "db_usuario": db_usuario,
        "usuario_admin": "admin",
        # None cuando la contrasena la eligio quien se registro: no se conoce ni
        # se muestra.
        "password_admin": password_admin if password_hash is None else None,
        "dias_de_prueba": dias_prueba or DIAS_DE_PRUEBA,
    }


def main():
    parser = argparse.ArgumentParser(description="Da de alta un consultorio en la plataforma.")
    parser.add_argument("slug", help="Subdominio: solo minusculas, numeros y guiones")
    parser.add_argument("nombre", help="Nombre visible del consultorio")
    parser.add_argument("email", help="Email de contacto y del usuario admin")
    parser.add_argument("--plan", default="basico")
    parser.add_argument("--password", default=None, help="Password del admin (si no, se genera)")
    args = parser.parse_args()

    try:
        alta = dar_de_alta(args.slug, args.nombre, args.email, args.plan, args.password)
    except AltaInvalida as exc:
        print(f"No se pudo dar de alta: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - se informa y se corta
        print(f"Error dando de alta '{args.slug}': {exc}")
        return 1

    print()
    print(f"  Consultorio:   {alta['nombre']}")
    print(f"  Subdominio:    {alta['slug']}")
    print(f"  Base de datos: {alta['db_nombre']} (usuario {alta['db_usuario']})")
    print(f"  Prueba:        {alta['dias_de_prueba']} dias")
    print()
    print(f"  Usuario:    {alta['usuario_admin']}")
    print(f"  Contrasena: {alta['password_admin']}")
    print()
    print("  Anotala: no se vuelve a mostrar (se guarda hasheada).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
