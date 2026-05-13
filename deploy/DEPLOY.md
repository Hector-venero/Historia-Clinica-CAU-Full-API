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

# 🛠 7. Comandos útiles

```bash
docker compose down -v
docker compose --env-file .env up -d --build
```

---

# 👨‍💻 Autor
**Héctor Manuel de Jesús Venero Monzón**