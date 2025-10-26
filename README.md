# 🏥 Historia Clínica CAU - Full API (Flask + React + Docker + MySQL + BFA + Seguridad avanzada)

Este proyecto implementa un sistema web integral para la gestión de **historias clínicas unificadas**, desarrollado como **Trabajo Final de Ingeniería en Telecomunicaciones (UNSAM)**.  
La arquitectura combina **Flask + React + MySQL + Blockchain Federal Argentina (BFA)**, con enfoque en **seguridad, trazabilidad y auditoría de integridad médica**.

---

## 🚀 Novedades (Octubre 2025)

- 🔄 Arquitectura **modular y segura** con `Flask + Gunicorn + Nginx`
- 🔐 **Flask-Talisman** y cabeceras CSP/HTTPS activadas
- 🌍 **CORS restringido** solo al frontend autorizado
- ⛓️ **Integración nativa con Blockchain Federal Argentina (BFA)** vía nodo `geth`
- 🧩 **Hashing SHA-256** y publicación en BFA
- 📜 **Verificación automática** entre hash local y blockchain
- 🧱 Orquestación completa con `Docker Compose`
- 🧾 **Sesiones expiran automáticamente** en 1 hora
- 📧 Sistema seguro de recuperación de contraseña por email (SMTP TLS)

---

## 📦 Estructura del Proyecto

```bash
📦 historia_clinica_bfa/
├── backend_flask/
│   └── app/
│       ├── routes/                # Endpoints por módulo (auth, pacientes, blockchain, etc.)
│       ├── utils/                 # Hashing, PDF, integridad, auditorías
│       ├── start.sh               # Script de arranque híbrido (Flask / Gunicorn)
│       ├── config.py              # Config global (lectura .env)
│       ├── main.py                # Entry principal Flask
│       ├── Dockerfile             # Imagen híbrida dev/prod
│       └── requirements.txt
│
├── db/init.sql                    # Estructura MySQL (pacientes, historias, auditorías)
├── frontend/                      # React + Vite + PrimeVue (UI UNSAM Pro)
│
├── nginx/default.conf             # Reverse proxy seguro (HTTP/HTTPS)
├── bfa-node/                      # Nodo Geth dev o BFA real
├── .env                           # Variables de entorno (DB, Mail, Blockchain, Flask)
└── docker-compose.yml             # Orquestación de servicios
```

---

## 🧰 Tecnologías Principales

| Capa | Tecnología |
|------|-------------|
| **Frontend** | React (Vite, PrimeVue, Tailwind, Sakai Template) |
| **Backend** | Flask, Flask-Login, Flask-Mail, Flask-Talisman |
| **Base de Datos** | MySQL 8.0 |
| **Blockchain** | Blockchain Federal Argentina (BFA, Geth) |
| **Servidor Web** | Nginx (reverse proxy seguro) |
| **Contenedores** | Docker + Docker Compose |
| **Hash / PDF** | hashlib (SHA-256), ReportLab |
| **Seguridad** | CSP, CORS, HTTPS, Scrypt password hashing |

---

## 🛡️ Seguridad

- 🔒 **Cabeceras HTTP seguras** (CSP, X-Frame-Options, HSTS, Referrer-Policy)
- 🌐 **HTTPS listo** con soporte para certificados Let's Encrypt
- ⚙️ **Flask-Talisman** protege contra ataques XSS / clickjacking
- 🔐 **Contraseñas cifradas con Scrypt (Werkzeug)**
- ⏱️ **Sesiones expiran a los 60 minutos**
- 🧍 **Roles jerárquicos:** `director`, `profesional`, `administrativo`
- 📧 **Recuperación de contraseña** con token firmado y link seguro
- 🧩 **Acceso protegido** por `@login_required`
- 🧰 **CORS limitado** al dominio del frontend React autorizado

---

## ⛓️ Blockchain Federal Argentina (BFA)

El sistema incluye integración directa con la **BFA**, mediante un contenedor `geth` configurado en modo `--dev` para pruebas.  
En producción, se reemplaza por el nodo permisionado oficial de BFA.

**Flujo de integridad:**
1. Cada historia clínica genera un hash SHA-256 consolidado.  
2. El hash se guarda localmente y opcionalmente se publica en la BFA.  
3. La verificación compara hash local ↔ blockchain.  
4. Cada auditoría se registra en la tabla `auditorias_blockchain`.  

📂 Código relevante:  
`app/utils/blockchain_utils.py` y `app/routes/blockchain_routes.py`

---

## 🐳 Despliegue con Docker Compose

### 1️⃣ Clonar repositorio

```bash
git clone https://github.com/Hector-venero/Historia-Clinica-CAU-Full-API.git
cd Historia-Clinica-CAU-Full-API
```

### 2️⃣ Crear archivo `.env`

Ejemplo base:

```env
# Flask
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=clave_super_segura

# MySQL
DB_HOST=db
DB_USER=hc_app
DB_PASSWORD=HC_App_2025!
DB_NAME=hc_bfa

# Mail (SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=hectorvenero2908@gmail.com
MAIL_PASSWORD=typyayxujklnyskg
MAIL_DEFAULT_SENDER=hectorvenero29hv@gmail.com

# Blockchain (BFA)
PRIVATE_KEY_BFA=03ca4edb5fb0dff310f92f8421cfbb1f3b5b2bb54ac9b9e3314b133fb7daae2b
ADDRESS_BFA=0x71562b71999873DB5b286dF957af199Ec94617F7

# Frontend
FRONTEND_URL=http://localhost:5173
```

### 3️⃣ Construir y levantar entorno

```bash
docker compose --env-file .env up -d --build
```

### 4️⃣ Verificar logs

```bash
docker logs historia_web | grep Running
docker ps
```

**Salida esperada:**
```
🚀 Running in PRODUCTION mode (Gunicorn)
```

---

## 🌍 Acceso

- Frontend: [http://localhost](http://localhost)
- Backend API: [http://localhost/api](http://localhost/api)
- Nodo BFA: `http://localhost:8545`

Usuario demo:
| Usuario | Contraseña |
|----------|-------------|
| `admin` | `admin123` |

---

## ⚙️ Entornos soportados

| Modo | Configuración | Ejecución |
|------|----------------|------------|
| **Desarrollo** | `FLASK_ENV=development` | Flask con auto-reload |
| **Producción** | `FLASK_ENV=production` | Gunicorn (multi-worker) |

Cambio de entorno → modificar `.env` y ejecutar:
```bash
docker compose down -v && docker compose up -d --build
```

---

## 📚 Documentación Técnica

Incluye diagramas y análisis técnico en `/docs/`:

- Arquitectura general Flask + React + BFA  
- Diagrama E/R MySQL  
- Flujo de integridad Blockchain  
- Comparativa PoW vs PoA  
- Descripción técnica de la BFA permisionada  
- Seguridad de red y cifrado de datos  

---

## 📬 Autor

**Héctor Venero**  
Ingeniería en Telecomunicaciones – UNSAM (ECyT)  
📧 hectorvenero29hv@gmail.com  
🔗 [LinkedIn](https://www.linkedin.com/in/hector-venero-8493a1154/)  
💻 [GitHub](https://github.com/Hector-venero)

🧠 *"Integridad, interoperabilidad y transparencia médica — Blockchain aplicada a la gestión sanitaria en Argentina."*