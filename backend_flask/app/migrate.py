"""Runner de migraciones SQL.

Se ejecuta desde start.sh en cada arranque del contenedor, antes de levantar
la app. Aplica en orden los .sql de MIGRATIONS_DIR que todavia no fueron
aplicados, y registra el resultado en la tabla schema_migrations.

Decisiones de diseno, todas surgidas de fallas reales:

- El split de sentencias entiende comentarios y literales. Un parser que solo
  cuenta comillas se rompe con un apostrofe dentro de un comentario (por
  ejemplo "doesn't"), y termina mandando el archivo entero como una sola
  sentencia. Eso produce el error 2014 "Commands out of sync" y, peor, hace
  que un fallo en la primera sentencia se lleve puestas todas las demas.

- Se guarda el checksum del archivo. Sin el, editar una migracion ya aplicada
  no se detecta: la DB vieja se queda con la version anterior y una DB nueva
  aplica la nueva, y ambas divergen en silencio.

- Una migracion se marca aplicada solo si TODAS sus sentencias pasaron. Si
  queda a medias se registra como 'parcial' y se reintenta en el proximo
  arranque.

- La tolerancia a errores de "ya existe" solo aplica a sentencias de una sola
  clausula. MySQL evalua un ALTER compuesto de forma atomica: si una clausula
  choca, se pierde el statement entero, y tolerarlo dejaria la migracion
  marcada como aplicada con columnas o constraints faltantes.
"""

import hashlib
import os
import pathlib
import sys

from mysql.connector import Error

# database.py vive en el mismo directorio (/app) cuando corre en el contenedor.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from database import DB_CONFIG  # noqa: E402

MIGRATIONS_DIR = pathlib.Path(os.getenv("MIGRATIONS_DIR", "/app/migrations"))

# Las migraciones necesitan DDL (CREATE/ALTER), pero el usuario de la app tiene
# a proposito solo SELECT/INSERT/UPDATE/DELETE (ver db/init.sql): no queremos
# que un bug de la app pueda borrar una tabla. Por eso migrate.py se conecta con
# credenciales propias y elevadas, y cae a las de la app solo si no se definen.
# Se usa `or` y no un default: docker compose pasa las variables no definidas
# como cadena vacia, no como ausentes, asi que "" tiene que contar como "no
# configurado" o terminariamos intentando conectar sin password.
MIGRATION_USER = os.getenv("DB_MIGRATION_USER") or "root"
MIGRATION_PASSWORD = os.getenv("DB_MIGRATION_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD") or None


def get_migration_connection(retries=10, delay=3):
    """Conexion con privilegios de DDL para aplicar migraciones."""
    import time

    import mysql.connector

    config = dict(DB_CONFIG)
    if MIGRATION_PASSWORD is not None:
        config["user"] = MIGRATION_USER
        config["password"] = MIGRATION_PASSWORD

    ultimo_error = None
    for intento in range(retries):
        try:
            conn = mysql.connector.connect(**config)
            if conn.is_connected():
                return conn
        except Error as exc:
            ultimo_error = exc
            print(f"Esperando a MySQL {intento + 1}/{retries}: {exc}")
            time.sleep(delay)
    raise RuntimeError(
        f"No se pudo conectar a MySQL como '{config['user']}' para migrar: {ultimo_error}"
    )

# Errores de "el objeto ya existe". Se toleran solo en sentencias de una sola
# clausula, para poder adoptar el tracking sobre una DB migrada a mano.
ERRORES_YA_EXISTE = {
    1050,  # tabla ya existe
    1060,  # columna duplicada
    1061,  # indice duplicado
    1826,  # foreign key duplicada
}

LOCK_NAME = "historia_clinica_migraciones"
LOCK_TIMEOUT = 60


def split_statements(sql):
    """Parte un script SQL en sentencias.

    Reconoce comentarios de linea (-- y #), de bloque, identificadores con
    backticks y literales con comillas simples o dobles, incluyendo escapes
    con backslash y comillas duplicadas ('' dentro de un literal).
    """
    statements = []
    current = []
    i = 0
    n = len(sql)
    in_single = in_double = in_backtick = False

    while i < n:
        char = sql[i]
        siguiente = sql[i + 1] if i + 1 < n else ""
        en_literal = in_single or in_double or in_backtick

        # Comentarios: solo fuera de literales
        if not en_literal:
            if char == "-" and siguiente == "-":
                fin = sql.find("\n", i)
                i = n if fin == -1 else fin
                continue
            if char == "#":
                fin = sql.find("\n", i)
                i = n if fin == -1 else fin
                continue
            if char == "/" and siguiente == "*":
                fin = sql.find("*/", i + 2)
                i = n if fin == -1 else fin + 2
                continue

        # Escape con backslash dentro de un literal
        if en_literal and char == "\\" and not in_backtick:
            current.append(char)
            if i + 1 < n:
                current.append(sql[i + 1])
            i += 2
            continue

        # Comilla duplicada dentro de un literal ('' o "")
        if in_single and char == "'" and siguiente == "'":
            current.append("''")
            i += 2
            continue
        if in_double and char == '"' and siguiente == '"':
            current.append('""')
            i += 2
            continue

        if char == "'" and not in_double and not in_backtick:
            in_single = not in_single
        elif char == '"' and not in_single and not in_backtick:
            in_double = not in_double
        elif char == "`" and not in_single and not in_double:
            in_backtick = not in_backtick

        if char == ";" and not (in_single or in_double or in_backtick):
            sentencia = "".join(current).strip()
            if sentencia:
                statements.append(sentencia)
            current = []
        else:
            current.append(char)
        i += 1

    cola = "".join(current).strip()
    if cola:
        statements.append(cola)
    return statements


def es_alter_compuesto(sentencia):
    """True si es un ALTER TABLE con mas de una clausula.

    MySQL lo evalua de forma atomica, asi que un error de "ya existe" en una
    clausula invalida el statement completo. No se puede tolerar.
    """
    texto = sentencia.lstrip().upper()
    if not texto.startswith("ALTER TABLE"):
        return False
    return _contar_clausulas_alter(sentencia) > 1


def _contar_clausulas_alter(sentencia):
    """Cuenta clausulas de un ALTER separadas por comas de nivel superior."""
    profundidad = 0
    comas = 0
    in_single = in_double = in_backtick = False
    anterior = ""

    for char in sentencia:
        if char == "'" and not in_double and not in_backtick and anterior != "\\":
            in_single = not in_single
        elif char == '"' and not in_single and not in_backtick and anterior != "\\":
            in_double = not in_double
        elif char == "`" and not in_single and not in_double:
            in_backtick = not in_backtick
        elif not (in_single or in_double or in_backtick):
            if char == "(":
                profundidad += 1
            elif char == ")":
                profundidad -= 1
            elif char == "," and profundidad == 0:
                comas += 1
        anterior = char

    return comas + 1


def checksum(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def ensure_schema_migrations(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename VARCHAR(255) PRIMARY KEY,
            checksum CHAR(64) NULL,
            estado VARCHAR(20) NOT NULL DEFAULT 'ok',
            statements_aplicados INT NOT NULL DEFAULT 0,
            statements_total INT NOT NULL DEFAULT 0,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    # Alta de columnas para DBs donde la tabla ya existe con el esquema viejo
    # (solo filename + applied_at). Una clausula por sentencia a proposito.
    for columna, definicion in (
        ("checksum", "CHAR(64) NULL"),
        ("estado", "VARCHAR(20) NOT NULL DEFAULT 'ok'"),
        ("statements_aplicados", "INT NOT NULL DEFAULT 0"),
        ("statements_total", "INT NOT NULL DEFAULT 0"),
    ):
        try:
            cursor.execute(f"ALTER TABLE schema_migrations ADD COLUMN {columna} {definicion}")
        except Error as exc:
            if getattr(exc, "errno", None) != 1060:
                raise


def estado_migracion(cursor, filename):
    """Devuelve (estado, checksum) de una migracion, o None si no se registro."""
    cursor.execute(
        "SELECT estado, checksum FROM schema_migrations WHERE filename = %s",
        (filename,),
    )
    fila = cursor.fetchone()
    if not fila:
        return None
    return fila[0], fila[1]


def registrar(cursor, filename, sha, estado, aplicados, total):
    cursor.execute(
        """
        INSERT INTO schema_migrations
            (filename, checksum, estado, statements_aplicados, statements_total)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            checksum = VALUES(checksum),
            estado = VALUES(estado),
            statements_aplicados = VALUES(statements_aplicados),
            statements_total = VALUES(statements_total),
            applied_at = CURRENT_TIMESTAMP
        """,
        (filename, sha, estado, aplicados, total),
    )


def aplicar_migracion(cursor, migration):
    """Aplica una migracion. Devuelve (aplicados, total). Lanza si falla."""
    sql = migration.read_text(encoding="utf-8")
    sentencias = split_statements(sql)
    aplicados = 0

    for sentencia in sentencias:
        try:
            cursor.execute(sentencia)
        except Error as exc:
            errno = getattr(exc, "errno", None)
            if errno in ERRORES_YA_EXISTE and not es_alter_compuesto(sentencia):
                print(f"  - objeto ya existe, se continua: {exc}")
                aplicados += 1
                continue
            if errno in ERRORES_YA_EXISTE:
                raise RuntimeError(
                    f"{migration.name}: ALTER compuesto fallo con {errno}. "
                    f"MySQL lo evalua de forma atomica, asi que las demas clausulas "
                    f"tampoco se aplicaron. Parti el ALTER en una clausula por "
                    f"sentencia y volve a correr.\n  Sentencia: {sentencia[:200]}"
                ) from exc
            raise
        aplicados += 1

    return aplicados, len(sentencias)


def run_migrations():
    if not MIGRATIONS_DIR.exists():
        # Fallar y no arrancar: si el bind-mount de migraciones no esta, la app
        # levantaria contra un esquema viejo sin que nadie se entere.
        raise RuntimeError(
            f"No existe el directorio de migraciones ({MIGRATIONS_DIR}). "
            f"Revisa el volumen en docker-compose.yml, o defini MIGRATIONS_DIR."
        )

    conn = get_migration_connection()
    cursor = conn.cursor(buffered=True)
    tiene_lock = False
    try:
        # Lock de aplicacion: evita que dos arranques simultaneos (restart loop,
        # varios docker compose up) migren la misma DB a la vez.
        cursor.execute("SELECT GET_LOCK(%s, %s)", (LOCK_NAME, LOCK_TIMEOUT))
        if cursor.fetchone()[0] != 1:
            raise RuntimeError("No se pudo tomar el lock de migraciones; hay otra corriendo.")
        tiene_lock = True

        ensure_schema_migrations(cursor)
        conn.commit()

        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sha = checksum(migration.read_text(encoding="utf-8"))
            previo = estado_migracion(cursor, migration.name)

            if previo:
                estado_previo, sha_previo = previo
                if estado_previo == "ok":
                    if sha_previo and sha_previo != sha:
                        print(
                            f"AVISO: {migration.name} ya fue aplicada pero su contenido "
                            f"cambio desde entonces. Esta DB tiene la version anterior. "
                            f"Escribi una migracion nueva en vez de editar una aplicada."
                        )
                    else:
                        print(f"Ya aplicada: {migration.name}")
                    continue
                print(f"Reintentando migracion parcial: {migration.name}")

            print(f"Aplicando: {migration.name}")
            try:
                aplicados, total = aplicar_migracion(cursor, migration)
            except Exception:
                # Queda registrada como parcial para reintentar en el proximo arranque.
                registrar(cursor, migration.name, sha, "parcial", 0, 0)
                conn.commit()
                raise

            registrar(cursor, migration.name, sha, "ok", aplicados, total)
            conn.commit()
            print(f"  OK ({aplicados}/{total} sentencias)")
    finally:
        if tiene_lock:
            try:
                cursor.execute("SELECT RELEASE_LOCK(%s)", (LOCK_NAME,))
                cursor.fetchone()
            except Error:
                pass
        cursor.close()
        conn.close()


if __name__ == "__main__":
    usuario = MIGRATION_USER if MIGRATION_PASSWORD is not None else DB_CONFIG.get("user")
    print(f"Migraciones: {MIGRATIONS_DIR} (db={DB_CONFIG.get('database')}, usuario={usuario})")
    run_migrations()
