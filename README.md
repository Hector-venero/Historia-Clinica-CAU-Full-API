# 🏥 Historia Clínica CAU – Full API  
**Flask + React + MySQL + Docker + Nginx + Blockchain Federal Argentina (BFA)**

Sistema web para la gestión de **historias clínicas unificadas** y **agendas médicas**, desarrollado como **Trabajo Final de Ingeniería en Telecomunicaciones (UNSAM)**.

La solución integra un backend API en Flask, un frontend en React (Vite) y persistencia en MySQL, incorporando **auditoría de integridad** mediante hashing y (opcionalmente) publicación/verificación en **BFA**.

---

## ✅ Funcionalidades principales

- **Gestión de pacientes** (alta/edición/búsqueda) y visualización de información clínica.
- **Historias clínicas**: registro, consulta y exportación (según módulo implementado).
- **Turnos**:
  - Agenda por profesional.
  - **Agendas grupales**: turnos asociados a un **grupo profesional** (por especialidad/área).
  - Visualización tipo calendario con **FullCalendar** y listado/gestión.
- **Disponibilidades**: configuración de días y horarios de atención por profesional.
- **Bloqueos de agenda / ausencias**: impedir turnos en fechas específicas.
- **Seguridad**:
  - Autenticación con sesión (Flask-Login).
  - Roles con control de acceso (RBAC) tanto en backend (decoradores) como en frontend (guards).
  - Contraseñas hasheadas (Scrypt/Werkzeug).
  - CORS/CSP configurables (según tu setup).

---

## 👥 Roles del sistema (RBAC)

> Los nombres de roles son los que usás en la app (`director`, `profesional`, `administrativo`, `area`).

- **👑 Director**
  - Gestión completa: usuarios, grupos, auditoría y administración general.
- **👨‍⚕️ Profesional**
  - Manejo de su agenda personal, disponibilidades y acceso a funcionalidades clínicas según permisos.
- **🧾 Administrativo**
  - Operación diaria (pacientes/turnos) con permisos limitados.
- **🏥 Área**
  - Usuario “lógico” que representa una **especialidad/módulo** (ej. *Kinesiología*, *Salud Mental*) para soportar **agendas grupales**.
  - Puede ser miembro de grupos (junto con profesionales) para calendarización y asignación de turnos.

---

## 🧱 Arquitectura

```mermaid
graph TD
  Client[Frontend React/Vite] -->|HTTP| Nginx[Nginx Reverse Proxy]
  Nginx -->|/api| Flask[Backend Flask API]
  Flask --> DB[(MySQL)]
  Flask -->|Opcional| BFA[BFA / Geth]
  Flask -->|Opcional| SMTP[SMTP (recuperación contraseña)]
```

---

## 📦 Estructura del proyecto (resumen)

```bash
historia_clinica_bfa/
├── backend_flask/
│   └── app/
│       ├── routes/              # Endpoints (auth, turnos, grupos, etc.)
│       ├── utils/               # Decoradores permisos, hashing, helpers
│       ├── services/            # Servicios (BFA / lógica)
│       ├── main.py              # Entry Flask
│       └── Dockerfile
├── frontend/                    # React + Vite
├── nginx/                       # Reverse proxy
├── db/init.sql                  # Esquema MySQL
└── docker-compose.yml
```

---

## 🚀 Levantar el entorno con Docker

### 1) Clonar

```bash
git clone https://github.com/Hector-venero/Historia-Clinica-CAU-Full-API.git
cd Historia-Clinica-CAU-Full-API
```

### 2) Crear `.env`

```env
# Flask
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=cambia_esto_por_una_clave_segura

# MySQL
DB_HOST=db
DB_USER=hc_app
DB_PASSWORD=cambia_esto
DB_NAME=hc_bfa

# Frontend (si lo usás en CORS / links)
FRONTEND_URL=http://localhost

# Mail (opcional - recuperación de contraseña)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=tu_app_password
MAIL_DEFAULT_SENDER=tu_email@gmail.com

# Blockchain (opcional)
PRIVATE_KEY_BFA=0x...
ADDRESS_BFA=0x...
BFA_RPC_URL=http://bfa-node:8545
```

### 3) Build + up

```bash
docker compose --env-file .env up -d --build
```

### 4) Acceso

- **Frontend**: `http://localhost`
- **API**: `http://localhost/api`

---

## 🔐 Notas de seguridad recomendadas

- Guardar secretos en `.env` y excluirlos del repo.
- Configurar CORS para permitir solo el dominio del frontend.
- Mantener CSP/HSTS si servís por HTTPS.
- En producción: usar HTTPS real (certificados) y limitar puertos expuestos.

---

## ⛓️ Integridad y Blockchain (BFA)

Flujo típico:

1. Generar **hash SHA-256** del contenido clínico (o del registro consolidado).
2. Guardar el hash localmente.
3. (Opcional) Publicar el hash en BFA como transacción.
4. Verificar integridad comparando **hash BD ↔ hash blockchain**.

---

## 👤 Autor

**Héctor Venero** – Ingeniería en Telecomunicaciones (UNSAM – ECyT)  
- LinkedIn: https://www.linkedin.com/in/hector-venero-8493a1154/  
- GitHub: https://github.com/Hector-venero  

> “Integridad, interoperabilidad y transparencia médica — Blockchain aplicada a la gestión sanitaria en Argentina.”