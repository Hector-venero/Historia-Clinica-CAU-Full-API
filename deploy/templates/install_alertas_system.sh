#!/bin/bash
#
# Instalador del sistema de alertas diarias de agenda.
# Ejecutar desde la raiz del repositorio:
#
#     sudo bash deploy/templates/install_alertas_system.sh
#
# Variables opcionales:
#     ALERTAS_HORA=20     hora local Argentina en que se envian (default 20)
#     ALERTAS_MINUTO=0    minuto (default 0)
#     CONTAINER_NAME=historia_web

set -euo pipefail

echo "INSTALADOR DEL SISTEMA DE ALERTAS DE AGENDA - CAU"
echo "-------------------------------------------------"

CONTAINER_NAME="${CONTAINER_NAME:-historia_web}"
ALERTAS_HORA="${ALERTAS_HORA:-20}"
ALERTAS_MINUTO="${ALERTAS_MINUTO:-0}"
TZ_APP="America/Argentina/Buenos_Aires"

DESTINO="/usr/local/bin/alertas_turnos_cau.sh"
TEMPLATE="deploy/templates/alertas_turnos_cau.sh.template"

if [ ! -f "$TEMPLATE" ]; then
    echo "ERROR: no se encontro $TEMPLATE. Ejecutar desde la raiz del repositorio."
    exit 1
fi

# =============================
# 1. Instalar el script
# =============================
echo "Instalando $DESTINO..."
sed -e "s/{{CONTAINER_NAME}}/$CONTAINER_NAME/g" "$TEMPLATE" | sudo tee "$DESTINO" > /dev/null
sudo chmod +x "$DESTINO"
echo "  OK: $DESTINO"

# =============================
# 2. Carpeta de logs + rotacion
# =============================
echo "Creando /var/log/historia_cau..."
sudo mkdir -p /var/log/historia_cau
sudo chmod 750 /var/log/historia_cau

echo "Configurando logrotate..."
sudo tee /etc/logrotate.d/historia_cau_alertas > /dev/null <<'EOF'
/var/log/historia_cau/alertas_turnos.log {
    monthly
    rotate 12
    compress
    missingok
    notifempty
    copytruncate
}
EOF
echo "  OK: /etc/logrotate.d/historia_cau_alertas"

# =============================
# 3. Zona horaria del host
# =============================
# El cron corre en el HOST, no dentro del contenedor. Si el host esta en UTC,
# una linea "0 20 * * *" dispara a las 17:00 hora Argentina. Para que el horario
# sea el esperado se fija CRON_TZ en el crontab (soportado por cron de Debian/
# Ubuntu y por cronie en RHEL).
TZ_HOST="$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo 'desconocida')"
echo "Zona horaria del host: $TZ_HOST"
echo "Zona horaria de la app: $TZ_APP"

if [ "$TZ_HOST" != "$TZ_APP" ]; then
    echo "  AVISO: el host NO esta en hora Argentina."
    echo "  Se agrega CRON_TZ=$TZ_APP al crontab para corregirlo."
fi

# =============================
# 4. Programar cron
# =============================
CRON_LINE="$ALERTAS_MINUTO $ALERTAS_HORA * * * $DESTINO"

echo "Programando cron diario ($(printf '%02d:%02d' "$ALERTAS_HORA" "$ALERTAS_MINUTO") hora Argentina)..."

# Se reescribe el crontab quitando cualquier linea previa de este script, para que
# reinstalar no deje entradas duplicadas.
CRON_ACTUAL="$(sudo crontab -l 2>/dev/null | grep -v "alertas_turnos_cau.sh" | grep -v "^CRON_TZ=$TZ_APP$" || true)"

# IMPORTANTE: CRON_TZ aplica a todas las lineas que le siguen. Por eso se escribe
# DESPUES de las tareas ya existentes (ej. el backup diario de las 03:00) y justo
# antes de la nuestra: asi los jobs previos siguen corriendo en la hora del host,
# tal como fueron programados, y solo las alertas usan hora Argentina.
{
    [ -n "$CRON_ACTUAL" ] && echo "$CRON_ACTUAL"
    echo "CRON_TZ=$TZ_APP"
    echo "$CRON_LINE"
} | sudo crontab -

echo "  OK: $CRON_LINE"

# =============================
# 5. Verificacion
# =============================
echo ""
echo "Crontab de root:"
sudo crontab -l | sed 's/^/    /'
echo ""
echo "SISTEMA DE ALERTAS INSTALADO."
echo ""
echo "Probar ahora manualmente (envia mails reales):"
echo "    sudo $DESTINO && tail -20 /var/log/historia_cau/alertas_turnos.log"
echo ""
echo "Simular sin enviar (solo ver a quien le tocaria):"
echo "    docker exec $CONTAINER_NAME flask enviar-alertas"
