#!/usr/bin/env bash
#
# Compara los dos caminos por los que se llega al esquema de la base:
#
#   A) una instalación nueva:    db/init.sql actual  + db/migrations/
#   B) una instalación existente: db/init.sql viejo   + db/migrations/
#
# Las migraciones corren en los dos casos (start.sh las ejecuta en cada
# arranque), asi que lo unico que cambia es el punto de partida. Si los dos
# caminos no llegan al mismo esquema, hay algo que se agrego a init.sql sin su
# migracion correspondiente.
#
# Nada garantiza que coincidan, y ya pasó dos veces que una columna llegara solo
# a init.sql y rompiera en runtime sobre una base migrada:
#
#   - disponibilidades: el valor 'Domingo' del ENUM -> 1265 "Data truncated"
#   - grupos_profesionales.es_rehabilitacion        -> 1054 "Unknown column"
#
# Los dos aparecieron con la app andando. Este script los habría detectado antes.
#
# Uso:  bash scripts/comparar_esquemas.sh
# Requiere Docker. No toca la base del proyecto: levanta dos contenedores
# temporales en puertos propios y los elimina al terminar.

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS="comparacion"
BASE="hc_bfa"
TMP="$(mktemp -d)"

# El init.sql de referencia para el camino B: el que existía antes de que se
# incorporara el sistema de migraciones. Todo lo posterior debe estar en
# db/migrations/, que es justamente lo que este script verifica.
REF="${REF_INIT:-archivo/pre-reconciliacion-main}"

limpiar() {
    docker rm -f esquema_nuevo esquema_migrado >/dev/null 2>&1 || true
    rm -rf "$TMP"
}
trap limpiar EXIT

levantar() {
    local nombre="$1" puerto="$2"
    docker run -d --name "$nombre" \
        -e MYSQL_ROOT_PASSWORD="$PASS" -e MYSQL_DATABASE="$BASE" \
        -p "$puerto:3306" mysql:8.0 >/dev/null

    # Una consulta autenticada real, no `mysqladmin ping`: durante la
    # inicializacion MySQL levanta un servidor temporal que responde al ping
    # pero todavia no tiene puesta la clave de root, y la carga del esquema
    # fallaba con "Access denied".
    printf '  esperando a %s' "$nombre"
    for _ in $(seq 1 90); do
        if docker exec "$nombre" mysql -uroot -p"$PASS" -e "SELECT 1" >/dev/null 2>&1; then
            echo " listo"
            return 0
        fi
        printf '.'
        sleep 1
    done
    echo " TIMEOUT"
    return 1
}

# Vuelca el esquema como una lista ordenada de "tabla.columna tipo", en vez del
# CREATE TABLE crudo. Asi una columna agregada al final por un ALTER no aparece
# como diferencia solo por estar en otra posicion: lo unico que importa es que
# exista y con la misma definicion.
esquema_de() {
    docker exec "$1" mysql -uroot -p"$PASS" -N -B -e "
        SELECT CONCAT(TABLE_NAME, '.', COLUMN_NAME, '  ', COLUMN_TYPE,
                      IF(IS_NULLABLE='NO',' NOT NULL',''),
                      IFNULL(CONCAT(' DEFAULT ', COLUMN_DEFAULT), ''))
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA='$BASE' AND TABLE_NAME <> 'schema_migrations'
        ORDER BY TABLE_NAME, COLUMN_NAME;
    " 2>/dev/null
}

# Constraints e indices, tambien ordenados.
restricciones_de() {
    docker exec "$1" mysql -uroot -p"$PASS" -N -B -e "
        SELECT CONCAT(rc.TABLE_NAME, '.', rc.CONSTRAINT_NAME, ' -> ',
                      rc.REFERENCED_TABLE_NAME, ' ON DELETE ', rc.DELETE_RULE)
        FROM information_schema.REFERENTIAL_CONSTRAINTS rc
        WHERE rc.CONSTRAINT_SCHEMA='$BASE'
        ORDER BY rc.TABLE_NAME, rc.CONSTRAINT_NAME;
    " 2>/dev/null
}

# Contenedores de una corrida anterior interrumpida darian un resultado
# equivocado: la base ya tendria datos y el diff mostraria diferencias falsas.
docker rm -f esquema_nuevo esquema_migrado >/dev/null 2>&1 || true

echo "==> Levantando las dos bases"
levantar esquema_nuevo 13401
levantar esquema_migrado 13402

echo
echo "==> A) Base nueva: db/init.sql actual"
# --force: los init.sql traen sentencias administrativas (SET GLOBAL time_zone,
# CREATE USER) que fallan segun privilegios y abortarian el script del cliente.
# Acá solo interesa el esquema.
docker exec -i esquema_nuevo mysql --force -uroot -p"$PASS" < "$RAIZ/db/init.sql" 2>/dev/null

echo "==> B) Base existente: init.sql de $REF + migraciones"
if git -C "$RAIZ" rev-parse --verify --quiet "$REF" >/dev/null; then
    git -C "$RAIZ" show "$REF:db/init.sql" > "$TMP/init_viejo.sql"
else
    echo "    (no existe la referencia $REF; se usa el init.sql actual)"
    cp "$RAIZ/db/init.sql" "$TMP/init_viejo.sql"
fi
docker exec -i esquema_migrado mysql --force -uroot -p"$PASS" < "$TMP/init_viejo.sql" 2>/dev/null

# El python del sistema no suele tener mysql-connector; se prefiere el venv.
PY_BIN="$RAIZ/backend_flask/venv/bin/python"
[ -x "$PY_BIN" ] || PY_BIN="python3"

migrar() {
    DB_HOST=127.0.0.1 DB_PORT="$1" DB_USER=root DB_PASSWORD="$PASS" DB_NAME="$BASE" \
    MIGRATIONS_DIR="$RAIZ/db/migrations" \
        "$PY_BIN" "$RAIZ/backend_flask/app/migrate.py" 2>&1 |
        grep -E "Aplicando|OK \(|Traceback|Error" | sed 's/^/    /'
}

echo "    migrando la base nueva..."
migrar 13401
echo "    migrando la base existente..."
migrar 13402

echo
echo "==> Comparando"
{ esquema_de esquema_nuevo;   echo "--- FKs ---"; restricciones_de esquema_nuevo;   } > "$TMP/a.sql"
{ esquema_de esquema_migrado; echo "--- FKs ---"; restricciones_de esquema_migrado; } > "$TMP/b.sql"

if diff -u "$TMP/a.sql" "$TMP/b.sql" > "$TMP/diff.txt"; then
    echo "    OK: los dos caminos producen el mismo esquema."
    exit 0
fi

echo "    DIFERENCIAS (- solo en la base nueva, + solo en la migrada):"
echo
sed -n '3,$p' "$TMP/diff.txt" | grep -E '^[+-]' | sed 's/^/      /'
echo
echo "    Una linea que solo aparece en la base nueva es una definicion que"
echo "    quedo en init.sql sin su migracion: en produccion no va a existir."
exit 1
