# 🏥 Historia Clínica CAU – Full API  
**Flask + Vue 3 + MySQL + Docker + Nginx + Blockchain Federal Argentina (BFA)**

Sistema web para la gestión de **historias clínicas unificadas** y **agendas médicas**, desarrollado como **Trabajo Final de Ingeniería en Telecomunicaciones (UNSAM)**.

La solución integra un backend API en Flask, un frontend en Vue 3 (Vite + PrimeVue) y persistencia en MySQL, incorporando **auditoría de integridad** mediante hashing y (opcionalmente) publicación/verificación en **BFA**.

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
  - Contraseñas hasheadas con **bcrypt**.
  - La sesión vive en una cookie HttpOnly; el rol **no** se guarda en `localStorage`.
  - CORS/CSP configurables por entorno.

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
  Client["Frontend Vue 3 / Vite"] -->|HTTP| Nginx["Nginx Reverse Proxy"]
  Nginx -->|/api| Flask["Backend Flask API"]
  Nginx -->|/uploads| Files["Adjuntos (volumen)"]
  Flask --> DB[("MySQL")]
  Flask -->|Opcional| TSA["BFA TSA API"]
  Flask -->|Opcional| QBI["QBI2 (recetas)"]
  Flask -->|Opcional| SMTP["SMTP (recuperación y avisos)"]
```

---

## 📦 Estructura del proyecto (resumen)

```bash
historia_clinica_bfa/
├── backend_flask/
│   ├── app/
│   │   ├── routes/              # Endpoints (auth, turnos, grupos, recetas, etc.)
│   │   ├── utils/               # Permisos, hashing, clientes BFA/QBI, correo
│   │   ├── __init__.py          # App factory (registra los blueprints)
│   │   ├── migrate.py           # Runner de migraciones (corre al arrancar)
│   │   └── Dockerfile
│   └── tests/                   # pytest — no necesita MySQL
├── frontend/                    # Vue 3 + Vite + PrimeVue
├── nginx/                       # Reverse proxy
├── scripts/                     # Utilidades (comparar_esquemas.sh)
├── db/
│   ├── init.sql                 # Esquema inicial (solo en base vacía)
│   └── migrations/              # Cambios de esquema posteriores
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

# Migraciones. El usuario de la app solo tiene DML; las migraciones necesitan
# DDL (ALTER/CREATE/INDEX), por eso usan credenciales propias. Sin esto el
# backend no arranca: aplica las migraciones al iniciar y falla con un 1142.
MYSQL_ROOT_PASSWORD=cambia_esto
DB_MIGRATION_USER=root
DB_MIGRATION_PASSWORD=cambia_esto

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
BFA_TSA_URL=https://tsaapi.bfa.ar/api/tsa
```

### 3) Build + up

```bash
docker compose --env-file .env up -d --build
```

### 4) Acceso

- **Frontend**: `http://localhost`
- **API**: `http://localhost/api`

### 5) Desarrollo con recarga en caliente (sin nginx)

El stack de arriba sirve el frontend como build estático, así que cada cambio
exige reconstruir la imagen. Para desarrollar:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
    up -d db web frontend-dev
```

Queda en `http://localhost:5173` con HMR. Corre sobre `node:20-alpine`, así que
no hace falta tener Node instalado (Vite 7 exige ≥ 20.19).

---

## 🔐 Notas de seguridad recomendadas

- Guardar secretos en `.env` y excluirlos del repo.
- Configurar CORS para permitir solo el dominio del frontend.
- Mantener CSP/HSTS si servís por HTTPS.
- En producción: usar HTTPS real (certificados) y limitar puertos expuestos.

---

## ⛓️ Integridad y Blockchain (BFA TSA API)

**🛠️ Refactorización Arquitectónica (Rama `refactor/bfa-tsa-api`):**  
En esta rama se realizó una migración completa para dejar de depender de un nodo Geth local y utilizar la API oficial de Timestamp Authority (TSA) de la BFA.

**Resumen de los cambios y bugs solucionados:**
- **Infraestructura:** Se eliminó el contenedor `bfa-node` del `docker-compose.yml` y la librería `web3` de Python, aligerando drásticamente el consumo de RAM/CPU de la aplicación.
- **Backend:** Se reescribió `bfa_client.py` usando `requests` contra `tsaapi.bfa.ar`. El cliente devuelve la respuesta cruda **sin reintentar**: la TSA agrupa los hashes en lotes, así que entre el sellado y su confirmación responde `pending`, y eso **no** es una adulteración. Distinguir `pending` de `failure` es responsabilidad de quien llama.
- **Corrección de Hash:** Se arregló un bug donde el hash sellado difería del guardado en BD debido a un `.strip()`. Ahora se sella de forma exacta el `hash_local` de la BD.
- **Base de Datos:** Se ejecutó un `ALTER TABLE` para ampliar las columnas `tx_hash` y `hash_bfa` a `VARCHAR(512)`, soportando así los recibos extensos en formato Base64 que devuelve la TSA.
- **Frontend:** Se mejoró la tarjeta de auditoría clínica. El recibo TSA (`permanent_rd`) ahora se decodifica en el backend para mostrarle al usuario el **número de bloque exacto** y la **fecha/hora de sellado real** en la red.

**Flujo de Auditoría Actualizado:**

1. El sistema genera un **hash SHA-256** del contenido clínico consolidado y lo guarda localmente. El *payload* del hash está **versionado**: la forma del JSON es parte del algoritmo, así que agregar un campo cambiaría el hash de todas las historias y las ya ancladas dejarían de verificar. Cada historia registra con qué versión se calculó.
2. El hash se envía a la TSA de BFA (`tsaapi.bfa.ar/api/tsa/stamp/`), que devuelve un recibo. Cada sellado inserta una fila en **`anclajes_blockchain`**, que es **append-only**: la historia consolidada se recalcula con cada evolución nueva, así que un único puntero quedaría apuntando a un hash inexistente.
3. Para verificar, el sistema consulta la TSA con el recibo **de ese anclaje**, no con el estado actual. El resultado tiene **tres estados, no dos**: `success` y `failure` son veredictos y se auditan; `pending` significa que el lote todavía no cerró y no concluye nada.

También puede anclarse una **evolución individual**, con su propio hash y su propio recibo, para probar la integridad de un acto médico puntual sin depender del estado de la historia completa.

---

## 👤 Autor

**Héctor Venero** – Ingeniería en Telecomunicaciones (UNSAM – ECyT)  
- LinkedIn: https://www.linkedin.com/in/hector-venero-8493a1154/  
- GitHub: https://github.com/Hector-venero  

> “Integridad, interoperabilidad y transparencia médica — Blockchain aplicada a la gestión sanitaria en Argentina.”