#!/usr/bin/env bash
#
# Mueve los adjuntos de evoluciones a la estructura por cliente.
#
#   antes:   uploads/evoluciones/<id>/archivo.pdf
#   despues: uploads/<cliente>/evoluciones/<id>/archivo.pdf
#
# El id de la evolucion es autoincremental **por base de datos**. Con una base
# por consultorio, dos clientes tendrian ambos la evolucion 1 y sus archivos
# colisionarian en el mismo volumen. Por eso el cliente pasa a ser el primer
# segmento de la ruta.
#
# Es idempotente: si ya esta migrado, no hace nada.
#
# Uso:  bash scripts/migrar_adjuntos.sh [cliente]
#       cliente por defecto: "principal" (ver CLIENTE_POR_DEFECTO en
#       backend_flask/app/utils/adjuntos.py)

set -euo pipefail

CLIENTE="${1:-principal}"
CONTENEDOR="${CONTENEDOR_WEB:-historia_web}"
BASE="/app/uploads"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTENEDOR"; then
    echo "El contenedor $CONTENEDOR no esta corriendo."
    echo "Levantalo con: docker compose up -d web"
    exit 1
fi

echo "==> Cliente destino: $CLIENTE"

docker exec "$CONTENEDOR" sh -c "
    set -e
    cd '$BASE' 2>/dev/null || { echo '    No existe $BASE, nada que migrar.'; exit 0; }

    if [ ! -d evoluciones ]; then
        echo '    No hay uploads/evoluciones/. Nada que migrar.'
        exit 0
    fi

    if [ -d '$CLIENTE/evoluciones' ]; then
        echo '    Ya existe $CLIENTE/evoluciones/. Se fusiona lo que falte.'
    fi

    mkdir -p '$CLIENTE'

    # -n para no pisar lo ya migrado: si una carpeta existe en destino, se deja
    # la del destino y se informa, en vez de perder archivos en silencio.
    movidas=0
    for dir in evoluciones/*/; do
        [ -d \"\$dir\" ] || continue
        id=\$(basename \"\$dir\")
        destino='$CLIENTE/evoluciones'
        mkdir -p \"\$destino\"
        if [ -e \"\$destino/\$id\" ]; then
            echo \"    ya estaba: \$id (se deja el destino)\"
        else
            mv \"\$dir\" \"\$destino/\$id\"
            movidas=\$((movidas + 1))
        fi
    done

    # Solo se borra el directorio viejo si quedo vacio.
    rmdir evoluciones 2>/dev/null && echo '    evoluciones/ vacio, eliminado' || true

    echo \"    evoluciones movidas: \$movidas\"
"

echo
echo "==> Resultado"
docker exec "$CONTENEDOR" sh -c "ls -la '$BASE' 2>/dev/null | sed 's/^/    /'"
