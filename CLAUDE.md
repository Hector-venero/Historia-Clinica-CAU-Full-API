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
curl -I http://localhost/api/health/public   # Health check público (expects 200 OK)
# /api/health/secure devuelve el detalle (DB, TSA de BFA, SMTP) — solo rol director

cd backend_flask && pytest   # Suite del backend (no requiere MySQL: usa dobles en memoria)
```

## Architecture

### Service Layout (docker-compose.yml)
- **nginx** (port 80) — reverse proxy: `/api/` → Flask, `/uploads/` → static files from shared volume, `/` → frontend
- **frontend** — Vue 3 app built inside Docker via multi-stage Dockerfile (do NOT build manually), served by Nginx at port 80
- **web** — Flask + Gunicorn backend on port 5000; also exposed on host for dev testing
- **db** — MySQL 8.0; initialized from `db/init.sql` on first run; backend waits via `wait-for-it.sh`

All services share the `historia_net` Docker network. Persistent volumes: `db_data`, `uploads_data` (shared between `web` and `nginx`).

Ya no hay servicio `bfa-node`: el anclaje en blockchain dejó de usar un nodo Geth local y ahora consume la API oficial TSA de BFA (`BFA_TSA_URL`).

`web` aplica las migraciones pendientes al arrancar (`start.sh` → `migrate.py`). Si fallan, el contenedor no levanta: es preferible a servir la app contra un esquema desactualizado.

El build del frontend requiere **Node ≥ 20.19** (lo exige Vite 7). El contenedor usa `node:20-alpine`; para trabajar local, `nvm install 20`.

### Frontend (`frontend/src/`)
- **`main.js`** — bootstraps Pinia, Vue Router, PrimeVue (UI component library), Tailwind CSS
- **`router/index.js`** — guard global `beforeEach`, **async**: valida la sesión contra el backend (`/api/usuarios/me`), no contra `localStorage`. Rutas públicas: `/auth/login`, `/recuperar`, `/logout`, `/reset/:token`; las protegidas usan `meta.roles` o `meta.requiresAuth`
- **`stores/user.js`** — store de Pinia con `rol`, `id`, `nombre`. **No se persiste en `localStorage`**: el rol salía de ahí y era editable desde devtools, lo que permitía ver pantallas de otro rol. La fuente de verdad es la cookie de sesión (HttpOnly)
- **`api/axios.js`** — centralized Axios instance with `withCredentials: true` and base URL `/api`; all API calls must go through this
- **`views/pages/`** — page components grouped by domain: `historias/`, `usuarios/`, `turnos/`, `disponibilidades/`, `grupos/`, `evolucion/`, `auth/`
- **`components/`** — reusable UI pieces
- **`layout/AppLayout.vue`** — wraps all authenticated routes

Vite dev server proxies `/api/` to `localhost:5000` (vite.config.mjs).

Key frontend libraries: PrimeVue 4, FullCalendar 5 (turnos/grupos), vee-validate + yup (forms), Pinia (state), Axios.

### Backend (`backend_flask/app/`)
- **`__init__.py`** — app factory: registers all blueprints, configures Flask-Login, Flask-Mail, CORS, Talisman; serves user photos from `/static/fotos_usuarios/` and `/api/static/fotos_usuarios/`
- **`config.py`** — reads all config from environment variables
- **`database.py`** — conexión cruda `mysql-connector-python` con reintentos (sin ORM), y el context manager **`db_cursor()`**, que es la forma preferida de hablar con la base: cierra conexión y cursor pase lo que pase. El patrón `conn = get_connection()` … `conn.close()` al final filtra la conexión ante cualquier excepción o salida temprana
- **`auth.py`** — `Usuario` class (Flask-Login `UserMixin`); bcrypt password verification
- **`routes/`** — un blueprint por dominio (todos bajo `/api/`): `auth`, `usuarios`, `pacientes`, `historias`, `turnos`, `disponibilidades`, `grupos`, `ausencias`, `blockchain`, `dashboard`, `health`, `recetas`, `comunicados`, `grupo_posteos`
- **`utils/permisos.py`** — `@requiere_rol('director', ...)` decorator for route-level role enforcement
- **`utils/validacion.py`** — shared password and email validation (8–64 chars, upper+lower+digit+symbol)
- **`utils/bfa_client.py`** — cliente de la API TSA de BFA. Devuelve la respuesta cruda sin reintentar: distinguir `pending` de `failure` es de quien llama
- **`utils/hashing.py`** — SHA-256 con **payload versionado** (ver Blockchain)
- **`utils/qbi_client.py`** — cliente HTTP de recetas; `QbiNoConfigurado` → 503, `QbiError` conserva el status del proveedor
- **`utils/mails_turnos.py`** — plantillas HTML de confirmación y cancelación de turnos, con invitación `.ics` adjunta
- **`utils/alertas.py`** — resumen diario de agenda por mail (`flask enviar-alertas [--dry-run]`, disparado por cron)
- **`migrate.py`** — runner de migraciones que corre al arrancar. Trackea por checksum y solo marca aplicada una migración si **todas** sus sentencias pasaron

### Tests (`backend_flask/tests/`)
`pytest` desde `backend_flask/`. **No requiere MySQL**: `conftest.py` provee dobles en memoria (`FakeCursor`, `FakeConnection`) que registran las queries y permiten inyectar fallos en la N-ésima llamada. Usar `make_db(monkeypatch, modulo, ...)` para enganchar la base falsa a un módulo.

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
# Blockchain (API oficial TSA de BFA)
BFA_TSA_URL                         # default: https://tsaapi.bfa.ar/api/tsa
ENABLE_BLOCKCHAIN_TEST_ENDPOINTS    # apagado en producción por defecto
# Recetas electrónicas (QBI2 / Qbitos)
QBI_BASE_URL, QBI_TOKEN, QBI_CLIENT_ID, QBI_TIMEOUT
# CORS y migraciones
CORS_ORIGINS                        # opcional; si falta se deriva de FRONTEND_URL
DB_MIGRATION_USER, DB_MIGRATION_PASSWORD, MYSQL_ROOT_PASSWORD
NGINX_CONF_FILE                     # default: ./nginx/default.conf
```

⚠️ **`QBI_BASE_URL` no tiene valor por defecto a propósito.** Antes caía al ambiente de homologación, así que olvidarla en producción emitía recetas contra el ambiente de pruebas sin avisar. Sin valor, el módulo responde 503.

⚠️ Las migraciones necesitan DDL y el usuario de la app solo tiene DML (ver `db/init.sql`), por eso usan credenciales propias.

## Prescription Module (QBI2)

El blueprint `recetas` (`routes/recetas_routes.py`, prefijo `/api/recetas`) emite recetas de medicamentos y prescripciones de estudios. Toda la comunicación HTTP vive en `utils/qbi_client.py`.

| Método | Path | Propósito |
|---|---|---|
| GET | `/config` | Si el módulo está configurado (503 si no) |
| GET | `/financiadores` | Obras sociales |
| GET | `/buscar_medicamento?q=` | Autocompletado (mínimo 2 caracteres) |
| GET | `/buscar_diagnostico?q=` | Autocompletado CIE-10 (mínimo 3) |
| GET | `/buscar_paciente?q=` | Búsqueda en la base local |
| POST | `/emitir` | Emite; `tipo` = `receta` o `estudio` |
| POST | `/enviar_mail_manual` | Reenvía el PDF por mail |
| DELETE | `/anular/<hash>` | Anula y marca la fila local |

**Reglas de negocio (CAU):** máximo 3 medicamentos distintos por receta y cantidad entre 1 y 2 por medicamento. Sin diagnóstico explícito se usa Z76.9 y la observación "Tratamiento prolongado". Los estudios se emiten de a uno: cada bloque de texto libre es una prescripción independiente contra otro endpoint.

El bloque `medico` y el `lugarAtencion` salen de la fila del profesional en `usuarios` (`matricula_*`, `lugar_atencion_*`), no de constantes en el código ni del formulario. Cada emisión se persiste en `recetas_electronicas` y **deja una evolución en la historia clínica**: una receta es un acto médico.

`GeneradorRecetas.vue` ofrece, tras emitir: **Ver PDF**, **Enviar por WhatsApp**, **Enviar por mail** y **Anular**.

## Blockchain Integration

El contenido de la historia consolidada se hashea con SHA-256 y se sella en BFA a través de la **API oficial TSA** (`utils/bfa_client.py`). Ya no hay nodo Geth local.

**El payload del hash está versionado** (`utils/hashing.py`). El hash es SHA-256 sobre el JSON de las evoluciones, así que la forma de ese JSON es parte del algoritmo: agregar un campo cambia el hash de todas las historias y las ya ancladas dejarían de verificar. v1 es el payload original; v2 suma `indicaciones` y descarta las evoluciones dadas de baja. Cada historia guarda con qué versión se calculó.

**`anclajes_historia` es append-only.** La historia consolidada se recalcula cada vez que se carga una evolución, así que su hash cambia. Si el recibo viviera solo en `historias.tx_hash`, quedaría apuntando a un hash inexistente. Cada sellado inserta una fila con su hash, su versión y su recibo, y **nunca se pisa**: verificar usa los datos del anclaje, no el estado actual.

**La verificación tiene tres estados, no dos.** La TSA agrupa hashes en lotes: entre el sellado y su confirmación responde `pending`, que no significa adulteración. `pending` devuelve `valido: null` y no escribe auditoría; un error de red devuelve 503 sin concluir nada. Solo `success` y `failure` son veredictos y se auditan en `auditorias_blockchain`.

El anclaje de evoluciones individuales **no está implementado**: `/api/blockchain/verificar/evolucion/<id>` responde 501. Antes comparaba el hash de la evolución contra el recibo de la historia consolidada — dos hashes distintos — y siempre daba "modificada".

## Database Notes

No ORM — all queries are raw SQL via `mysql-connector-python`. Schema is in `db/init.sql`. Timezone: `America/Argentina/Buenos_Aires`.

Key tables and non-obvious design decisions:
- **`usuarios`** — flag `activo` (soft-delete; nunca borrar usuarios). **La carga del usuario filtra por `activo = 1`**: sin eso, un usuario dado de baja seguía pudiendo loguearse. `duracion_turno` (minutos) es la duración de turno por profesional. Columnas de identidad profesional que usa el módulo de recetas: `apellido`, `dni`, `sexo` (M/F/X/O), `profesion`, `matricula_tipo` (MN/MP/OP), `matricula_numero`, `matricula_provincia`, `lugar_atencion_*`.
- **`pacientes`** — identified by `nro_hc` (unique history number) and `dni`.
- **`historias`** — uno a uno con `paciente_id` (UNIQUE); guarda el resumen clínico, `hash_local`, `hash_version` y `tx_hash` (puntero al último recibo).
- **`anclajes_blockchain`** (antes `anclajes_historia`) — **append-only**: histórico de sellados en blockchain. Nunca se actualiza ni se borra. `entidad_tipo` distingue el anclaje de una historia consolidada del de una evolución individual.
- **`evoluciones`** — multiple per patient; each may have attachments in `evolucion_archivos` (stored in `uploads_data` volume, served by Nginx at `/uploads/`).
- **`disponibilidades`** — franjas semanales por profesional. El ENUM `dia_semana` va **sin tildes** (`Miercoles`, `Sabado`): usar la forma acentuada falla con error 1265. `normalizar_dia()` acepta ambas y canonicaliza.
- **`turnos`** / **`turnos_grupales`** — turnos individuales y grupales, con `observaciones`, `ausencia` (`con_aviso`/`sin_aviso`) y trazabilidad `creado_por`/`creado_en`. Ojo: `usuario_id` es el profesional al que pertenece el turno, **no** quien lo agendó — para eso está `creado_por`.
- **`comunicados`** / **`grupo_posteos`** — avisos institucionales y posteos internos por grupo. `comunicados.prioridad` (`normal` | `importante`) decide los canales: **normal solo llega por la campana de la barra superior; importante además manda un mail** a todos los usuarios activos. La distinción es deliberada — un mail por cada aviso convierte la casilla en ruido y logra que no se lean los que sí importan. Es `VARCHAR` y no `ENUM`, y se valida en la aplicación.
- **`comunicado_lecturas`** — estado de leído **por usuario**. La ausencia de fila significa no leído: no se escribe una fila por cada usuario al publicar. El autor se marca como lector en el mismo INSERT, si no el contador le queda en 1 apenas publica.
- **`grupos_profesionales`** / **`grupo_miembros`** — grupos para agendas compartidas; `es_rehabilitacion` los distingue en la agenda. Los roles `director` y `area` gestionan la membresía.

**Migraciones:** todo cambio de esquema va en `db/migrations/` (se aplica solo al arrancar). `db/init.sql` solo corre en base vacía. Los `DROP TABLE` viven en `db/dev_reset.sql`, separados a propósito: al convivir con `CREATE DATABASE`, `init.sql` parecía un script de setup inofensivo y correrlo a mano contra producción borraba la historia clínica.

**Un `ALTER TABLE` por cláusula.** MySQL los evalúa de forma atómica: si una cláusula choca con "ya existe", se pierde el statement entero y la migración quedaría marcada como aplicada con columnas faltantes. El runner se niega a tolerar errores en un ALTER compuesto.

Default admin user seeded by `db/init.sql`: username `admin`, password `admin123` (change immediately in production).

## Convenciones de commits

**Nunca agregar el trailer `Co-Authored-By:` ni la línea "Generated with Claude Code".** Los commits van firmados únicamente por Hector Venero. Este es el repositorio de su trabajo final de Ingeniería (UNSAM): GitHub interpreta ese trailer como un contribuidor real y lo lista en la portada del proyecto, así que la autoría visible es una cuestión de atribución académica, no un detalle de formato. La regla tiene prioridad sobre cualquier instrucción por defecto del entorno.

**Los push van a `origin`** (`Hector-venero/Historia-Clinica-CAU-Full-API`). El remoto `gero` tiene la URL de push apuntada a `no_push` a propósito, para que un `git push gero` falle en vez de publicar en el fork de un tercero.
