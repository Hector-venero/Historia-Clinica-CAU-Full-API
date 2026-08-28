#!/usr/bin/env bash
#
# Restaura un consultorio desde una copia: su base y sus adjuntos.
#
# Restaurar a UNO SOLO sin tocar a los demas es la razon concreta por la que
# cada consultorio tiene su base. Con una base compartida, "restaurame el martes
# pasado" obligaria a elegir entre perder el trabajo de los otros clientes o
# hacer cirugia fila por fila.
#
# Uso:
#   bash scripts/restaurar_cliente.sh drlopez /var/backups/plataforma/drlopez/drlopez_2026-08-29_03-00.sql.gz
#
# Pide confirmacion escrita: sobrescribe la base entera del consultorio.

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTENEDOR_DB="${CONTENEDOR_DB:-historia_db}"
CONTENEDOR_WEB="${CONTENEDOR_WEB:-historia_web}"
PLATAFORMA_DB="${PLATAFORMA_DB_NAME:-plataforma}"

SLUG="${1:-}"
ARCHIVO="${2:-}"
ADJUNTOS="${3:-}"

if [ -z "$SLUG" ] || [ -z "$ARCHIVO" ]; then
    echo "Uso: $0 <slug> <archivo.sql.gz> [adjuntos.tar.gz]"
    exit 2
fi

if [ ! -f "$ARCHIVO" ]; then
    echo "No existe el archivo: $ARCHIVO"
    exit 1
fi

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

# La base sale del plano de control y no del nombre del archivo: el archivo se
# puede renombrar, y restaurar sobre la base equivocada seria irreparable.
# Sin -i: `docker exec -i` conecta stdin del script al del contenedor y se lo
# consume. La confirmacion que se pide mas abajo llegaba vacia y la restauracion
# se cancelaba sola. Solo lleva -i el comando que recibe el volcado por tuberia.
DB_NOMBRE=$(docker exec "$CONTENEDOR_DB" mysql -u"$DB_ADMIN_USER" -p"$DB_ADMIN_PASS" -N -B \
    -e "SELECT db_nombre FROM $PLATAFORMA_DB.clientes WHERE slug='$SLUG';" 2>/dev/null)

if [ -z "$DB_NOMBRE" ]; then
    echo "No existe el consultorio '$SLUG' en el plano de control."
    exit 1
fi

echo "==> Restauracion"
echo "    consultorio: $SLUG"
echo "    base:        $DB_NOMBRE"
echo "    desde:       $ARCHIVO"
echo
echo "    Esto REEMPLAZA todo el contenido actual de esa base."
echo "    Lo que se haya cargado despues de la copia se pierde."
echo
printf "    Escribi el slug del consultorio para confirmar: "
read -r confirmacion

if [ "$confirmacion" != "$SLUG" ]; then
    echo "    Cancelado."
    exit 1
fi

echo
echo "==> Restaurando la base"
if [[ "$ARCHIVO" == *.gz ]]; then
    gunzip -c "$ARCHIVO" | docker exec -i "$CONTENEDOR_DB" \
        mysql -u"$DB_ADMIN_USER" -p"$DB_ADMIN_PASS" "$DB_NOMBRE" 2>/dev/null
else
    docker exec -i "$CONTENEDOR_DB" \
        mysql -u"$DB_ADMIN_USER" -p"$DB_ADMIN_PASS" "$DB_NOMBRE" < "$ARCHIVO" 2>/dev/null
fi

if [ $? -ne 0 ]; then
    echo "    FALLO la restauracion de la base."
    exit 1
fi

tablas=$(docker exec "$CONTENEDOR_DB" mysql -u"$DB_ADMIN_USER" -p"$DB_ADMIN_PASS" -N -B \
    -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='$DB_NOMBRE';" 2>/dev/null)
echo "    ok: $tablas tablas"

if [ -n "$ADJUNTOS" ] && [ -f "$ADJUNTOS" ]; then
    echo
    echo "==> Restaurando los adjuntos"
    docker exec -i "$CONTENEDOR_WEB" tar -xzf - -C /app/uploads < "$ADJUNTOS"
    echo "    ok"
fi

echo
echo "==> Listo. Entra a verificar antes de avisarle al consultorio."
