#!/bin/bash

echo "🚀 INSTALADOR AUTOMÁTICO DEL SISTEMA DE BACKUPS CAU"
echo "--------------------------------------------------"

# =============================
# 1. Cargar .env del proyecto
# =============================
ENV_FILE="$(dirname $0)/../../.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ ERROR: No se encontró el archivo .env"
    exit 1
fi

set -o allexport
source "$ENV_FILE"
set +o allexport

# Variables que usarán los templates
MYSQL_USER="$DB_USER"
MYSQL_PASSWORD="$DB_PASSWORD"
MYSQL_DB="$DB_NAME"
MYSQL_HOST="$DB_HOST"

REMOTE_BACKUP_USER="${REMOTE_BACKUP_USER:-}"
REMOTE_BACKUP_HOST="${REMOTE_BACKUP_HOST:-}"

# =============================
# 2. Crear carpeta de backups
# =============================
echo "📁 Creando carpeta /var/backups/historia_cau..."
sudo mkdir -p /var/backups/historia_cau
sudo chmod 700 /var/backups/historia_cau

# =============================
# 3. Función generadora
# =============================
instalar_script() {
    local template="$1"
    local destino="$2"

    sed \
        -e "s/{{MYSQL_USER}}/$MYSQL_USER/g" \
        -e "s/{{MYSQL_PASSWORD}}/$MYSQL_PASSWORD/g" \
        -e "s/{{MYSQL_DB}}/$MYSQL_DB/g" \
        -e "s/{{MYSQL_HOST}}/$MYSQL_HOST/g" \
        -e "s/{{REMOTE_USER}}/$REMOTE_BACKUP_USER/g" \
        -e "s/{{REMOTE_HOST}}/$REMOTE_BACKUP_HOST/g" \
        "$template" | sudo tee "$destino" > /dev/null

    sudo chmod +x "$destino"
    echo "✔ Instalado: $destino"
}

# =============================
# 4. Instalar los scripts
# =============================
instalar_script "deploy/templates/backup_historia_cau.sh.template" "/usr/local/bin/backup_historia_cau.sh"
instalar_script "deploy/templates/restaurar_historia_cau.sh.template" "/usr/local/bin/restaurar_historia_cau.sh"
instalar_script "deploy/templates/copia_externa_historia_cau.sh.template" "/usr/local/bin/copia_externa_historia_cau.sh"

# =============================
# 5. Programar cron diario
# =============================
echo "🕒 Creando tarea CRON diaria (03:00)..."
( sudo crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/backup_historia_cau.sh" ) | sudo crontab -

# =============================
# 6. Primer backup
# =============================
echo "📦 Ejecutando backup inicial..."
sudo /usr/local/bin/backup_historia_cau.sh

echo "🎉 SISTEMA DE BACKUPS INSTALADO EXITOSAMENTE"
