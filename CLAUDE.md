# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sistema de gestión de Historia Clínica (medical records) for CAU (Centro de Atención de Urgencias) — UNSAM. Full-stack app with Flask backend, Vue 3 frontend, MySQL database, Nginx reverse proxy, and optional Ethereum/BFA blockchain integration for audit trails — all orchestrated via Docker Compose.

## Development Commands

### Full Stack (Docker)
```bash
docker compose up --build          # Build and start all services
docker compose up -d               # Start in background
docker compose logs -f web         # Tail Flask backend logs
docker compose logs -f frontend    # Tail frontend build logs
docker compose down                # Stop all services
docker compose down -v             # WARNING: destroys db_data, bfa_data, uploads_data volumes
```

### Frontend (Vue 3 + Vite)
```bash
cd frontend
npm install
npm run dev       # Dev server on http://localhost:5173
npm run build     # Production build → dist/
npm run lint      # ESLint with auto-fix (Vue, JS files)
```

### Backend (Flask)
The backend is intended to run inside Docker, but for local development:
```bash
cd backend_flask/app
pip install -r requirements.txt
# Requires a running MySQL instance and .env configured
flask run --host=0.0.0.0
```

### API Testing (curl)
```bash
cd frontend/tests
bash test_usuarios.sh   # Curl-based smoke tests for user endpoints (requires jq)
curl -I http://localhost/api/health   # Health check (expects 200 OK)
```

## Architecture

### Service Layout (docker-compose.yml)
- **nginx** (port 80) — reverse proxy: `/api/` → Flask, `/uploads/` → static files from shared volume, `/` → frontend
- **frontend** — Vue 3 app built inside Docker via multi-stage Dockerfile (do NOT build manually), served by Nginx at port 80
- **web** — Flask + Gunicorn backend on port 5000; also exposed on host for dev testing
- **db** — MySQL 8.0; initialized from `db/init.sql` on first run; backend waits via `wait-for-it.sh`
- **bfa-node** — Geth Ethereum node (port 8545 RPC); runs `--dev` mode; switch to mainnet config for production

All services share the `historia_net` Docker network. Persistent volumes: `db_data`, `bfa_data`, `uploads_data` (shared between `web` and `nginx`).

### Frontend (`frontend/src/`)
- **`main.js`** — bootstraps Pinia, Vue Router, PrimeVue (UI component library), Tailwind CSS
- **`router/index.js`** — global `beforeEach` guard; reads auth from `localStorage`; public routes: `/auth/login`, `/recuperar`, `/logout`, `/reset/:token`; protected routes use `meta.roles` or `meta.requiresAuth`
- **`stores/user.js`** — Pinia store; single source of truth for `rol`, `id`, `nombre`; synced to `localStorage`
- **`api/axios.js`** — centralized Axios instance with `withCredentials: true` and base URL `/api`; all API calls must go through this
- **`views/pages/`** — page components grouped by domain: `historias/`, `usuarios/`, `turnos/`, `disponibilidades/`, `grupos/`, `evolucion/`, `auth/`
- **`components/`** — reusable UI pieces
- **`layout/AppLayout.vue`** — wraps all authenticated routes

Vite dev server proxies `/api/` to `localhost:5000` (vite.config.mjs).

Key frontend libraries: PrimeVue 4, FullCalendar 5 (turnos/grupos), vee-validate + yup (forms), Pinia (state), Axios.

### Backend (`backend_flask/app/`)
- **`__init__.py`** — app factory: registers all blueprints, configures Flask-Login, Flask-Mail, CORS, Talisman; serves user photos from `/static/fotos_usuarios/` and `/api/static/fotos_usuarios/`
- **`config.py`** — reads all config from environment variables
- **`database.py`** — raw `mysql-connector-python` connection with retry logic (no ORM)
- **`auth.py`** — `Usuario` class (Flask-Login `UserMixin`); bcrypt password verification
- **`routes/`** — one blueprint per domain (all prefixed `/api/`): `auth`, `usuarios`, `pacientes`, `historias`, `turnos`, `disponibilidades`, `grupos`, `ausencias`, `blockchain`, `dashboard`, `health`, `recetas`
- **`utils/permisos.py`** — `@requiere_rol('director', ...)` decorator for route-level role enforcement
- **`utils/validacion.py`** — shared password and email validation (8–64 chars, upper+lower+digit+symbol)
- **`utils/bfa_client.py`** — Web3 client for BFA blockchain (web3==6.15.0)
- **`utils/hashing.py`** — SHA-256 hashing for medical record integrity
- **`utils/qbi_client.py`** — HTTP client for QBI2 prescription API (`buscar_medicamento`, `buscar_diagnostico`, `emitir_receta`, `get_financiadores`, `anular_receta`)

## Authentication & Roles

Session-based auth via Flask-Login (cookie). Four roles with descending privileges:

| Role | Access |
|---|---|
| `director` | Full admin, user CRUD, all data |
| `profesional` | Own agenda, assigned patients, schedule config |
| `administrativo` | Day-to-day operations, scheduling |
| `area` | Module/specialty representative, group calendars |

**Always enforce at both layers:**
- Backend: `@login_required` + `@requiere_rol(...)` decorators from `utils/permisos.py`
- Frontend: `meta: { roles: [...] }` on the route in `router/index.js`

Routes with only `meta: { requiresAuth: true }` are accessible to all authenticated roles.

## Key Configuration

Environment variables are loaded from `.env` (copy from `.env.example`):

```
FLASK_ENV, FLASK_DEBUG, SECRET_KEY
DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
FRONTEND_URL
VITE_API_URL=/api       # Passed as Docker build arg; set to /api in production
TZ=America/Argentina/Buenos_Aires
# Blockchain
PRIVATE_KEY_BFA, ADDRESS_BFA, BFA_RPC_URL
# QBI2 Prescriptions
QBI_BASE_URL, QBI_TOKEN, QBI_CLIENT_ID
```

## Prescription Module (QBI2)

The `recetas` blueprint (`routes/recetas.py`) integrates with the QBI2 external API for electronic prescriptions. `utils/qbi_client.py` handles all HTTP calls to QBI2. Routes:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/recetas/financiadores` | List health insurance providers (financiadores) |
| GET | `/api/recetas/buscar_medicamento?q=` | Autocomplete medication search |
| GET | `/api/recetas/buscar_diagnostico?q=` | Autocomplete CIE-10 diagnosis search |
| POST | `/api/recetas/emitir` | Emit prescription; returns `recetas[0].s3Link` (PDF) and `receta_hash` |
| DELETE | `/api/recetas/anular/<hash>` | Void an emitted prescription |

The `medico` block in `emitir_receta` is built from `current_user` fields (`apellido`, `dni`, `sexo`, `profesion`, `matricula_tipo`, `matricula_numero`, `matricula_provincia`). Clinic address is defined as module-level constants in `recetas.py` (prefixed `CLINICA_`).

The patient payload always includes a hardcoded `cuil` field (HML test value). If `idFinanciador` and `nroAfiliado` are provided, a `cobertura` dict is added to the patient payload.

`GeneradorRecetas.vue` loads financiadores on mount, shows an optional obra social selector + nro afiliado field, and after a successful emission exposes three action buttons: **Ver PDF** (opens S3 link), **Enviar por WhatsApp** (pre-fills `api.whatsapp.com/send`), and **Anular Receta** (calls DELETE and clears the hash/link).

## Blockchain Integration

Medical record content is hashed (SHA-256 via `utils/hashing.py`) and the hash can be published to BFA (Blockchain Federal Argentina, Ethereum-compatible). `tx_hash` is stored in the `historias` table; `auditorias_blockchain` logs each verification attempt. The `bfa-node` service runs `--dev` mode locally; mainnet config is commented out in `docker-compose.yml`.

## Database Notes

No ORM — all queries are raw SQL via `mysql-connector-python`. Schema is in `db/init.sql`. Timezone: `America/Argentina/Buenos_Aires`.

Key tables and non-obvious design decisions:
- **`usuarios`** — has `activo` flag (soft-delete pattern; never hard-delete users). `duracion_turno` (minutes) is per-professional appointment slot length. Professional identity columns used by the prescription module: `apellido`, `dni`, `sexo` (M/F/X/O), `profesion`, `matricula_tipo` (MN/MP), `matricula_numero`, `matricula_provincia`. The seeded `admin` user carries HML test values for these fields.
- **`pacientes`** — identified by `nro_hc` (unique history number) and `dni`.
- **`historias`** — one-to-one with `paciente_id` (UNIQUE constraint); stores the main clinical summary plus `hash_local` and `tx_hash`.
- **`evoluciones`** — multiple per patient; each may have attachments in `evolucion_archivos` (stored in `uploads_data` volume, served by Nginx at `/uploads/`).
- **`disponibilidades`** — weekly recurring availability slots per professional.
- **`turnos`** — individual appointments, bounded by `fecha_inicio`/`fecha_fin`.
- **`grupos_profesionales`** / **`grupo_miembros`** — professional groups for shared calendars; `director` and `area` roles can manage membership.

Default admin user seeded by `db/init.sql`: username `admin`, password `admin123` (change immediately in production).
