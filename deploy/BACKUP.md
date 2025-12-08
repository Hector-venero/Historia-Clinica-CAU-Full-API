# 🔐 Sistema Automático de Backups – Historia Clínica CAU

Este documento describe la instalación, uso y restauración del sistema automático de respaldos para la base de datos **hc_bfa**.  
Está diseñado para funcionar tanto en desarrollo como en producción.

---

# 📌 1. ¿Qué incluye el sistema?

✔ Backup diario automático (03:00 AM)  
✔ Cifrado automático con GPG  
✔ Almacenamiento seguro en `/var/backups/historia_cau`  
✔ Script de restauración compatible con Docker  
✔ Script de copia externa opcional  
✔ Instalador que lee las credenciales desde `.env`

---

# 📁 2. Instalación del sistema de backups

Desde la raíz del proyecto ejecutar:

```bash
sudo bash deploy/install_backup_system.sh
```

El instalador realiza automáticamente:

1. Lee credenciales del archivo `.env`:
   - `DB_HOST`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`
   - `REMOTE_BACKUP_USER` (opcional)
   - `REMOTE_BACKUP_HOST` (opcional)

2. Crea la carpeta:
   ```
   /var/backups/historia_cau
   ```

3. Genera los scripts finales en:
   ```
   /usr/local/bin/backup_historia_cau.sh
   /usr/local/bin/restaurar_historia_cau.sh
   /usr/local/bin/copia_externa_historia_cau.sh
   ```

4. Concede permisos y registra los CRON  
5. Ejecuta un backup inicial de prueba

---

# 🧪 3. Ejecutar un backup manual

```bash
sudo /usr/local/bin/backup_historia_cau.sh
```

Salida esperada:

```
📦 Generando backup...
🔐 Cifrando backup...
✅ Backup listo: /var/backups/historia_cau/backup_YYYY-MM-DD_HH-MM.sql.gpg
```

---

# 🗂 4. Ubicación de los respaldos

Todos los backups quedan guardados en:

```
/var/backups/historia_cau/
```

Formato:

```
backup_YYYY-MM-DD_HH-MM.sql.gpg
```

---

# 📤 5. Copia externa (opcional)

Configurar en `.env`:

```
REMOTE_BACKUP_USER=usuario
REMOTE_BACKUP_HOST=ip_o_dominio
```

Ejecutar:

```bash
sudo /usr/local/bin/copia_externa_historia_cau.sh
```

Envía los backups hacia:

```
usuario@IP:/backups/historia_cau/
```

---

# 🚨 6. Restauración de emergencia (Disaster Recovery)

⚠ **ADVERTENCIA: restaura la base y reemplaza completamente los datos actuales.**

Restaurar:

```bash
sudo /usr/local/bin/restaurar_historia_cau.sh /var/backups/historia_cau/backup_XXXX.sql.gpg
```

Flujo recomendado:

1️⃣ Apagar los contenedores  
```bash
docker compose down
```

2️⃣ Restaurar la base  
```bash
sudo /usr/local/bin/restaurar_historia_cau.sh archivo.gpg
```

3️⃣ Levantar todo otra vez  
```bash
docker compose up -d
```

---

# 🔍 7. Verificar el CRON diario

```bash
sudo crontab -l
```

Debe aparecer:

```
0 3 * * * /usr/local/bin/backup_historia_cau.sh
```

---

# 🧯 8. Troubleshooting

### ❌ 1045 Access denied
Asegurate de que el usuario `backup_user` existe dentro de MySQL (tu init.sql ya lo crea).

### ❌ Host desconocido en copia externa
Verificá que `.env` tenga valores válidos:

```
REMOTE_BACKUP_HOST=IP
REMOTE_BACKUP_USER=usuario
```

### ❌ No se genera backup
Verificar permisos:

```bash
sudo chmod 700 /var/backups/historia_cau
sudo chmod +x /usr/local/bin/backup_historia_cau.sh
```

---

# 🎯 9. Resumen

✔ Backup diario y cifrado  
✔ Scripts instalados automáticamente  
✔ Restauración simple y segura  
✔ Integración absoluta con `.env`  
✔ Listo para producción UNSAM  

---

# 👤 Autor

**Héctor Manuel de Jesús Venero Monzón**  
Proyecto Final – Ingeniería en Telecomunicaciones – UNSAM  
*“Implementación de Blockchain para la Gestión Unificada de Historias Clínicas en Argentina”*