#!/usr/bin/env bash
#
# Da de alta un consultorio en la plataforma.
#
#   bash scripts/alta_cliente.sh <slug> "<nombre>" <email> [plan]
#
# Ejemplo:
#   bash scripts/alta_cliente.sh drlopez "Consultorio Dr. Lopez" lopez@mail.com
#
# Es un envoltorio: la logica vive en backend_flask/app/alta_cliente.py, que es
# lo mismo que va a invocar el registro autoservicio. Asi no hay dos caminos de
# alta que puedan divergir.
#
# Crea la base del cliente, su usuario de MySQL con permisos solo sobre ella,
# aplica las migraciones y siembra el usuario admin.

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Uso: bash scripts/alta_cliente.sh <slug> \"<nombre>\" <email> [plan]"
    echo
    echo "  slug    subdominio: minusculas, numeros y guiones (drlopez)"
    echo "  nombre  nombre visible del consultorio"
    echo "  email   contacto y usuario admin"
    exit 1
fi

SLUG="$1"
NOMBRE="$2"
EMAIL="$3"
PLAN="${4:-basico}"
CONTENEDOR="${CONTENEDOR_WEB:-historia_web}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTENEDOR"; then
    echo "El contenedor $CONTENEDOR no esta corriendo."
    echo "Levantalo con: docker compose up -d web"
    exit 1
fi

echo "==> Dando de alta '$SLUG'"
docker exec \
    -e PYTHONPATH=/ \
    "$CONTENEDOR" \
    python -m app.alta_cliente "$SLUG" "$NOMBRE" "$EMAIL" --plan "$PLAN"
