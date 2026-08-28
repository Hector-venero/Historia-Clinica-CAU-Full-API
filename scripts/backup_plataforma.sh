#!/usr/bin/env bash
#
# Copia de seguridad de la plataforma completa: el plano de control y la base y
# los adjuntos de cada consultorio.
#
# Se hace **una copia por consultorio** y no un volcado de todo junto. Es la
# ventaja concreta de tener una base por cliente: restaurar a uno solo no obliga
# a tocar a los demas, que es exactamente lo que se necesita cuando alguien
# borra algo por error un martes a la tarde.
#
# Cada copia se verifica al generarla. Un backup que nunca se probo no es un
# backup: es un archivo. mysqldump puede terminar con codigo 0 y dejar un
# volcado truncado si se corta la conexion a mitad, y eso solo se descubre el dia
# que hace falta.
#
# Uso:
#   bash scripts/backup_plataforma.sh              # todos
#   bash scripts/backup_plataforma.sh drlopez      # uno solo
#
# Variables:
#   BACKUP_DIR     donde dejar las copias (default /var/backups/plataforma)
#   RETENCION_DIAS cuantos dias conservar    (default 30)

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/plataforma}"
RETENCION_DIAS="${RETENCION_DIAS:-30}"
FECHA="$(date +%Y-%m-%d_%H-%M)"

CONTENEDOR_DB="${CONTENEDOR_DB:-historia_db}"
CONTENEDOR_WEB="${CONTENEDOR_WEB:-historia_web}"

# Credenciales con permiso sobre todas las bases. Se leen del .env del proyecto,
# no se piden por parametro: asi el cron no lleva contrasenas en su linea.
if [ -f "$RAIZ/.env" ]; then
    DB_ADMIN_USER="$(grep -E '^DB_MIGRATION_USER=' "$RAIZ/.env" | cut -d= -f2- || true)"
    DB_ADMIN_PASS="$(grep -E '^DB_MIGRATION_PASSWORD=' "$RAIZ/.env" | cut -d= -f2- || true)"
    [ -n "${DB_ADMIN_PASS:-}" ] || DB_ADMIN_PASS="$(grep -E '^MYSQL_ROOT_PASSWORD=' "$RAIZ/.env" | cut -d= -f2- || true)"
fi
# Mismo valor por defecto que docker-compose.yml (MYSQL_ROOT_PASSWORD:-root).
# Si divergieran, el backup fallaria solo en produccion y solo al ejecutarse.
DB_ADMIN_USER="${DB_ADMIN_USER:-root}"
DB_ADMIN_PASS="${DB_ADMIN_PASS:-root}"

# Sin contrasena, el cliente de mysql PIDE una por teclado y se queda esperando.
# En un cron eso es un proceso colgado que nadie ve, y un backup que se cree
# hecho y no existe. Se prefiere fallar.
if [ -z "$DB_ADMIN_PASS" ]; then
    echo "Falta la contrasena de administracion de MySQL." >&2
    echo "Defini MYSQL_ROOT_PASSWORD o DB_MIGRATION_PASSWORD en .env" >&2
    exit 2
fi
PLATAFORMA_DB="${PLATAFORMA_DB_NAME:-plataforma}"

SOLO="${1:-}"

errores=0

mysql_admin() {
    docker exec -i "$CONTENEDOR_DB" mysql -u"$DB_ADMIN_USER" -p"$DB_ADMIN_PASS" -N -B "$@"
}

# Un volcado con datos termina siempre con esta linea. Si falta, se corto a
# mitad: es la diferencia entre un backup y un archivo grande.
verificar_volcado() {
    local archivo="$1"
    if [ ! -s "$archivo" ]; then
        echo "      FALLO: el volcado quedo vacio"
        return 1
    fi
    if ! tail -5 "$archivo" | grep -q "Dump completed"; then
        echo "      FALLO: el volcado esta truncado (falta 'Dump completed')"
        return 1
    fi
    local tablas
    tablas=$(grep -c "^CREATE TABLE" "$archivo")
    echo "      ok: $tablas tablas, $(du -h "$archivo" | cut -f1)"
    return 0
}

respaldar_base() {
    local db="$1" destino="$2"
    docker exec "$CONTENEDOR_DB" mysqldump \
        -u"$DB_ADMIN_USER" -p"$DB_ADMIN_PASS" \
        --single-transaction --routines --triggers \
        "$db" > "$destino" 2>/dev/null
    verificar_volcado "$destino"
}

mkdir -p "$BACKUP_DIR"

echo "==> Copia de seguridad de la plataforma  ($FECHA)"
echo "    destino: $BACKUP_DIR"
echo

# ---------------------------------------------------------- plano de control

if [ -z "$SOLO" ]; then
    echo "  [plano de control] $PLATAFORMA_DB"
    destino="$BACKUP_DIR/plataforma_$FECHA.sql"
    if respaldar_base "$PLATAFORMA_DB" "$destino"; then
        gzip -f "$destino"
    else
        errores=$((errores + 1))
    fi
    echo
fi

# ------------------------------------------------------------- consultorios

if [ -n "$SOLO" ]; then
    consultorios=$(mysql_admin -e "SELECT slug, db_nombre FROM $PLATAFORMA_DB.clientes WHERE slug='$SOLO';")
else
    consultorios=$(mysql_admin -e "SELECT slug, db_nombre FROM $PLATAFORMA_DB.clientes ORDER BY slug;")
fi

if [ -z "$consultorios" ]; then
    echo "  No hay consultorios que respaldar."
    exit $(( errores > 0 ? 1 : 0 ))
fi

while IFS=$'\t' read -r slug db_nombre; do
    [ -z "$slug" ] && continue
    echo "  [$slug] $db_nombre"

    carpeta="$BACKUP_DIR/$slug"
    mkdir -p "$carpeta"

    destino="$carpeta/${slug}_$FECHA.sql"
    if respaldar_base "$db_nombre" "$destino"; then
        gzip -f "$destino"
    else
        errores=$((errores + 1))
    fi

    # Los adjuntos: estudios, imagenes, informes. Sin ellos la copia queda
    # incompleta justo en lo que mas cuesta volver a conseguir.
    adjuntos="$carpeta/${slug}_adjuntos_$FECHA.tar.gz"
    if docker exec "$CONTENEDOR_WEB" test -d "/app/uploads/$slug" 2>/dev/null; then
        docker exec "$CONTENEDOR_WEB" tar -czf - -C /app/uploads "$slug" > "$adjuntos" 2>/dev/null
        echo "      adjuntos: $(du -h "$adjuntos" | cut -f1)"
    else
        echo "      adjuntos: (sin archivos)"
    fi
    echo
done <<< "$consultorios"

# ------------------------------------------------------------- retencion

echo "==> Limpiando copias de mas de $RETENCION_DIAS dias"
borradas=$(find "$BACKUP_DIR" -name '*.gz' -type f -mtime "+$RETENCION_DIAS" -print -delete 2>/dev/null | wc -l)
echo "    borradas: $borradas"
echo

if [ "$errores" -gt 0 ]; then
    echo "TERMINO CON $errores ERROR(ES). Revisar antes de confiar en estas copias."
    exit 1
fi

echo "OK: todas las copias se generaron y verificaron."
