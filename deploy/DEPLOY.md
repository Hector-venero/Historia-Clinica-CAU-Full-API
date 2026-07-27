# 
Guía de Deploy – Historia Clínica CAU (UNSAM) 
Este documento describe el procedimiento oficial para desplegar la aplicación **Historia Clínica CAU – Full API (Flask + React + Docker + Nginx + BFA)** en un entorno productivo.

---

#  1. Requisitos previos

- Servidor Linux con:
  - Docker ≥ 24
  - Docker Compose ≥ 2
- Acceso SSH
- Acceso al repositorio GitHub:
  - `git@github.com:Hector-venero/Historia-Clinica-CAU-Full-API.git`
- Archivo `.env` de producción (NO se sube al repositorio)
- Puerto 80 (y 443 si se usa SSL) habilitados

---

#  2. Estructura del proyecto

```
Historia-Clinica-CAU/
│
├── backend_flask/         # API Flask (Gunicorn en producción)
├── frontend/              # React + Vite
├── nginx/                 # Configuración Nginx
├── db/                    # Archivos SQL iniciales
├── bfa-node/              # Nodo Blockchain BFA (Geth en modo dev)
├── docker-compose.yml
└── .env                   # Variables de entorno (local del servidor)
```

---

#  3. Despliegue paso a paso

---

##  Paso 1 — Clonar el repositorio

```bash
git clone git@github.com:Hector-venero/Historia-Clinica-CAU-Full-API.git
cd Historia-Clinica-CAU-Full-API
```

---

##  Paso 2 — Crear el archivo `.env`

Copiar el archivo `.env` en la raíz del proyecto.

Ejemplo mínimo de producción:

```
FLASK_ENV=production
FLASK_DEBUG=False

VITE_API_URL=/api
FRONTEND_URL=https://mi-dominio.com

DB_HOST=db
DB_USER=hc_app
DB_PASSWORD=***
DB_NAME=hc_bfa
```

⚠️ En producción **NO deben usarse URLs localhost**.

---

## 🔹 Paso 3 — (IMPORTANTE) No ejecutar `npm run build` manualmente

El build del frontend **ya no se hace a mano**.

Ahora se genera automáticamente dentro del contenedor Docker:

```dockerfile
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
```

y luego:

```dockerfile
FROM nginx
COPY --from=build /app/dist /usr/share/nginx/html
```

Esto garantiza builds reproducibles y confiables.

---

## 🔹 Paso 4 — Levantar la aplicación

```bash
docker compose --env-file .env up -d --build
```

Esto crea y levanta los siguientes servicios:

| Servicio | Función |
|---------|---------|
| `historia_web` | Backend Flask (Gunicorn) |
| `historia_frontend` | Construcción del frontend |
| `historia_nginx` | Servidor web + reverse proxy |
| `historia_db` | Base MySQL |
| `bfa-node` | Nodo blockchain BFA |

---

# 🔍 4. Validaciones después del deploy

---

## ✔ Validar contenedores activos

```bash
docker ps
```

---

## ✔ Verificar que Nginx está sirviendo el build final

```bash
docker exec -it historia_nginx ls /usr/share/nginx/html
```

---

## ✔ Probar la API

```bash
curl -I http://localhost/api/health
```

Esperado:

```
200 OK
```

---

#  5. Acceso a la aplicación

### Sin dominio
```
http://<IP-del-servidor>
```

### Con dominio
```
https://historia-cau.unsam.edu.ar
```

---

#  6. Habilitar HTTPS

```bash
sudo certbot --nginx -d dominio.com
```

---

# 📧 7. Alertas diarias de agenda

Cada profesional recibe por mail el resumen de su agenda del día siguiente.

El envío **no es automático hasta instalar el cron**. El código expone un comando
CLI (`flask enviar-alertas`), pero nada lo dispara solo.

## Instalación (una sola vez, desde la raíz del repo)

```bash
sudo bash deploy/templates/install_alertas_system.sh
```

Esto:

1. Instala `/usr/local/bin/alertas_turnos_cau.sh`
2. Crea `/var/log/historia_cau/` y su rotación mensual (logrotate)
3. Agrega la tarea cron diaria a las **20:00 hora Argentina**

Para usar otro horario:

```bash
sudo ALERTAS_HORA=18 ALERTAS_MINUTO=30 bash deploy/templates/install_alertas_system.sh
```

Reinstalar es seguro: no duplica entradas en el crontab.

## Zona horaria (importante)

El cron corre en el **host**, no dentro del contenedor. Si el VPS está en UTC,
una línea `0 20 * * *` dispararía a las 17:00 hora Argentina.

Por eso el instalador agrega `CRON_TZ=America/Argentina/Buenos_Aires` al crontab.
Se escribe **después** de las tareas ya existentes (como el backup de las 03:00),
así solo afecta a las alertas y no corre el horario de los demás jobs.

## Verificación

```bash
sudo crontab -l
tail -20 /var/log/historia_cau/alertas_turnos.log
```

Probar a mano (⚠️ envía mails reales):

```bash
sudo /usr/local/bin/alertas_turnos_cau.sh
```

Ver a quién le tocaría, sin instalar nada:

```bash
docker exec historia_web flask enviar-alertas
```

## Quién recibe el mail

Profesionales `activo=1` con **disponibilidad horaria cargada y activa** para el
día de la semana de mañana. Si no tienen turnos ese día, igual reciben el mail
indicando que la agenda está vacía.

## Diagnóstico

El script devuelve código `1` y deja el motivo en el log si:

- el contenedor `historia_web` no está corriendo;
- el proceso no llegó al final (típicamente, la DB no responde);
- hubo errores en el envío de alguno de los mails.

---

# 🛠 8. Comandos útiles

```bash
docker compose down -v
docker compose --env-file .env up -d --build
```

---

# 👨‍💻 Autor
**Héctor Manuel de Jesús Venero Monzón**