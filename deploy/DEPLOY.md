# 🚀 Guía de Deploy – Historia Clínica CAU (UNSAM)

Este documento describe el procedimiento oficial para desplegar la aplicación **Historia Clínica CAU – Full API (Flask + React + Docker + BFA)** en el servidor productivo.

---

## 🧩 1️⃣ Requisitos previos

- Acceso al servidor donde se ejecutará el proyecto.
- Docker y Docker Compose instalados.
- Acceso al repositorio GitHub:  
  👉 [https://github.com/Hector-venero/Historia-Clinica-CAU-Full-API](https://github.com/Hector-venero/Historia-Clinica-CAU-Full-API)
- Copia local del archivo `.env` (no se sube al repo por seguridad).

---

## ⚙️ 2️⃣ Estructura del proyecto

```
Historia-Clinica-CAU-Full-API/
│
├── backend_flask/           # API Flask (Python)
├── frontend/                # Interfaz React (Vite)
├── nginx/                   # Configuración Nginx
├── db/                      # Scripts SQL
├── bfa-node/                # Nodo Blockchain (geth)
├── docker-compose.yml
└── .env                     # Variables de entorno (local del servidor)
```

---

## 🧱 3️⃣ Pasos de instalación y despliegue

### 🔹 Paso 1. Clonar el repositorio

```bash
git clone git@github.com:Hector-venero/Historia-Clinica-CAU-Full-API.git
cd Historia-Clinica-CAU-Full-API
```

---

### 🔹 Paso 2. Copiar el archivo `.env`


### 🔹 Paso 3. Generar el build del frontend (React)

```bash
cd frontend
npm install
npm run build
cd ..
```

Esto generará la carpeta `frontend/dist` con los archivos productivos de la interfaz web.

> ⚠️ Es importante ejecutar este paso dentro del servidor, ya que Nginx servirá directamente este `dist`.  
> Si no se hace, se mostrará la plantilla base de Sakai Vue.

---

### 🔹 Paso 4. Levantar todos los servicios

Desde la raíz del proyecto:

```bash
docker compose --env-file .env up -d --build
```

Esto levantará los siguientes contenedores:

| Contenedor | Descripción |
|-------------|--------------|
| `historia_web` | Backend Flask |
| `historia_db` | Base de datos MySQL |
| `bfa-node` | Nodo Blockchain (Geth modo dev) |
| `historia_frontend` | Build React (Vite) |
| `historia_nginx` | Proxy inverso Nginx (sirve frontend y /api) |

---

### 🔹 Paso 5. Verificar contenedores activos

```bash
docker ps
```

Deberían aparecer los 5 contenedores listados arriba en estado `Up`.

---

### 🔹 Paso 6. Validar que Nginx sirva el build correcto

Entrar al contenedor y revisar el contenido del build:

```bash
docker exec -it historia_nginx bash
cat /usr/share/nginx/html/index.html | grep "<title>"
```

Debe mostrar:
```
<title>Historia Clínica CAU</title>
```

Si en cambio muestra “Sakai Vue” o “PrimeVue Template”, significa que el `npm run build` no se ejecutó correctamente.

---

### 🔹 Paso 7. Acceder desde el navegador

```
https://tornamap.galileo.ar:51170/
```

o

```
http://tornamap.galileo.ar
```

Debería mostrarse la interfaz React real (login de Historia Clínica CAU) con conexión al backend Flask y Blockchain BFA.

---

## 🧰 4️⃣ Comandos útiles

### 🔸 Ver logs de un servicio
```bash
docker logs historia_web
```

### 🔸 Reconstruir todo desde cero
```bash
docker compose down -v
docker compose --env-file .env up -d --build
```

### 🔸 Entrar al contenedor Flask
```bash
docker exec -it historia_web bash
```

### 🔸 Entrar al contenedor Nginx
```bash
docker exec -it historia_nginx bash
```

---

## 🔒 5️⃣ Notas de seguridad

- El archivo `.env` **no debe subirse a GitHub**.  
  Contiene credenciales de base de datos y llaves privadas de BFA.
- En producción, se recomienda configurar HTTPS con Certbot:
  ```bash
  sudo certbot --nginx -d historia-cau.unsam.edu.ar
  ```
  y descomentar el bloque HTTPS en `nginx/default.conf`.

---

## ✅ Resultado esperado

Tras seguir estos pasos:
- La app se mostrará correctamente en el navegador.
- Nginx servirá el build de React desde `frontend/dist`.
- Las peticiones `/api/...` llegarán al backend Flask.
- El nodo BFA se ejecutará localmente para registrar los hashes de las historias clínicas.

---

🧾 **Autor:**  
Héctor Manuel de Jesús Venero Monzón  
Proyecto Final – Ingeniería en Telecomunicaciones – UNSAM  
`Implementación de Blockchain para la Gestión Unificada de Historias Clínicas en Argentina`