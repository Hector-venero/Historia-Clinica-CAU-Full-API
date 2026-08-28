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
docker compose down -v             # WARNING: destroys db_data, uploads_data volumes
```

La app queda en **http://localhost** (puerto 80, nginx). No en `:5173` ni `:8080`. El backend también se publica en `:5000`, solo para depurar.

### Modo desarrollo sin nginx (`docker-compose.dev.yml`)

El stack normal sirve el frontend como build estático detrás de **dos** capas de nginx (el proxy `nginx` y el propio contenedor `frontend`, que también es nginx). Para desarrollar eso cuesta: cada cambio exige reconstruir la imagen y no hay recarga en caliente.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db web frontend-dev
# queda en http://localhost:5173, con HMR
docker compose stop nginx frontend    # si venían levantados
```

Corre sobre `node:20-alpine` **a propósito**: Vite 7 exige Node ≥ 20.19 y en la máquina hay 18.19, con lo que `npm run dev` local falla con `crypto.hash is not a function`. `node_modules` va en un volumen propio para que el bind mount no exponga el de la máquina.

El destino del proxy sale de `VITE_PROXY_TARGET`: dentro de la red de Docker el backend es `http://web:5000`, no `localhost` (que sería el propio contenedor).

### Frontend (Vue 3 + Vite)
```bash
cd frontend
npm install
npm run dev       # Dev server on http://localhost:5173 (requiere Node >= 20.19)
npm run build     # Production build → dist/
npm run lint      # Solo reporta. NO reescribe archivos
npm run lint:fix  # Aplica las correcciones
```

⚠️ `lint` y `lint:fix` están separados a propósito: cuando `lint` corría con `--fix`, reescribía ~20 archivos como efecto secundario de "verificar", y eso llegó a chocar con un `git stash` y casi se pierde trabajo.

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

bash scripts/comparar_esquemas.sh   # Verifica que init.sql + migraciones y el
                                     # init.sql viejo + migraciones lleguen al
                                     # mismo esquema. Levanta dos MySQL
                                     # temporales; no toca la base del proyecto
```

## Architecture

### Service Layout (docker-compose.yml)
- **nginx** (port 80) — reverse proxy: `/api/` → Flask, `/` → frontend
- **frontend** — Vue 3 app built inside Docker via multi-stage Dockerfile (do NOT build manually), served by Nginx at port 80
- **web** — Flask + Gunicorn backend on port 5000, **publicado solo en `127.0.0.1`**
- **db** — MySQL 8.0; initialized from `db/init.sql` on first run; backend waits via `wait-for-it.sh`

All services share the `historia_net` Docker network. Persistent volumes: `db_data`, `uploads_data`.

⚠️ **nginx ya NO sirve `/uploads/` ni monta ese volumen.** Publicaba los adjuntos clínicos sin autenticación: los mismos archivos que la API devolvía con 401 se descargaban con 200 sin sesión. Ahora los sirve solo Flask, que exige `@login_required`, y el volumen no se monta para que una configuración futura no pueda volver a exponerlos. Las rutas se arman en `utils/adjuntos.py`, nunca a mano.

⚠️ **El puerto 5000 está atado a `127.0.0.1` a propósito.** Publicado en todas las interfaces es una puerta al backend que saltea nginx, y con él el HTTPS y el límite de tamaño de subida. Sigue sirviendo para depurar desde la propia máquina.

`docker-compose.prod.yml` agrega los ajustes de producción de la plataforma (ver más abajo). Ojo: **`command` en un override de Compose reemplaza al de base, no se suma** — por eso el `command` de `db` allí repite la zona horaria y los timeouts.

Ya no hay servicio `bfa-node`: el anclaje en blockchain dejó de usar un nodo Geth local y ahora consume la API oficial TSA de BFA (`BFA_TSA_URL`).

`web` aplica las migraciones pendientes al arrancar (`start.sh` → `migrate.py`). Si fallan, el contenedor no levanta: es preferible a servir la app contra un esquema desactualizado.

El build del frontend requiere **Node ≥ 20.19** (lo exige Vite 7). El contenedor usa `node:20-alpine`; para trabajar local, `nvm install 20`.

### Frontend (`frontend/src/`)
- **`main.js`** — bootstraps Pinia, Vue Router, PrimeVue (UI component library), Tailwind CSS
- **`router/index.js`** — guard global `beforeEach`, **async**: valida la sesión contra el backend (`/api/usuarios/me`), no contra `localStorage`. Rutas públicas: `/auth/login`, `/recuperar`, `/logout`, `/reset/:token`; las protegidas usan `meta.roles` o `meta.requiresAuth`
- **`stores/user.js`** — store de Pinia. **No se persiste en `localStorage`**: el rol salía de ahí y era editable desde devtools, lo que permitía ver pantallas de otro rol. La fuente de verdad es la cookie de sesión (HttpOnly). Además del usuario básico guarda los **campos profesionales** (`dni`, `matricula_*`, `lugar_atencion_*`, …), enumerados en `CAMPOS_PROFESIONALES`: `/api/usuarios/me` ya los devolvía y `setUser` los descartaba, con lo que la pantalla de recetas nunca daba el perfil por completo y el botón de emitir quedaba deshabilitado para siempre
- **`api/axios.js`** — centralized Axios instance with `withCredentials: true` and base URL `/api`; all API calls must go through this
- **`views/pages/`** — page components grouped by domain: `historias/`, `usuarios/`, `turnos/`, `disponibilidades/`, `grupos/`, `evolucion/`, `auth/`, `recetas/`, `comunicados/`, `Agenda/`
- **`components/`** — reusable UI pieces, incluida `ComunicadosCampana.vue` (campana de la barra superior)
- **`layout/AppLayout.vue`** — wraps all authenticated routes
- **`assets/calendar-medical.css`** — tema común de FullCalendar, compartido por `Turnos.vue` y `CalendarioGrupo.vue`

Vite dev server proxies `/api/` al backend; el destino sale de `VITE_PROXY_TARGET` y por defecto es `localhost:5000` (vite.config.mjs).

**Modo oscuro:** se activa con la clase `app-dark` en `<html>` (`layout/composables/layout.js`), y `tailwind.config.js` la declara como `darkMode: ['class', '[class*="app-dark"]']`. Todo color necesita su variante `dark:`. Usar la escala **`surface`**, que en el rango 200–800 resuelve a variables de PrimeUI (`--p-surface-*`) y sigue el tema; los valores 0/50/100/900/950 están fijados en `tailwind.config.js`. Un `bg-white` o un `text-gray-800` sueltos dejan la pantalla en claro sobre una app oscura.

Key frontend libraries: PrimeVue 4, FullCalendar 5 (turnos/grupos), vee-validate + yup (forms), Pinia (state), Axios.

**Caché del frontend en producción:** `frontend/nginx.conf` sirve `index.html` con `no-cache` y `/assets/` con un año e `immutable`. No es un detalle: sin `Cache-Control`, nginx manda solo `ETag`/`Last-Modified` y el navegador aplica **caché heurística**. Aplicado a `index.html` —el único archivo con nombre fijo, y el que apunta a los assets con hash— eso hace que después de cada deploy se siga viendo la versión anterior, y no hay rebuild que lo arregle: solo Ctrl+Shift+R.

### Backend (`backend_flask/app/`)
- **`__init__.py`** — app factory: registers all blueprints, configures Flask-Login, Flask-Mail, CORS, Talisman; serves user photos from `/static/fotos_usuarios/` and `/api/static/fotos_usuarios/`
- **`config.py`** — reads all config from environment variables
- **`database.py`** — conexión cruda `mysql-connector-python` con reintentos (sin ORM), y el context manager **`db_cursor()`**, que es la forma preferida de hablar con la base: cierra conexión y cursor pase lo que pase. El patrón `conn = get_connection()` … `conn.close()` al final filtra la conexión ante cualquier excepción o salida temprana
- **`auth.py`** — `Usuario` class (Flask-Login `UserMixin`). Las contraseñas se hashean con **scrypt** vía `werkzeug.security` (`generate_password_hash(..., method="scrypt")`), no con bcrypt: en la base se ven como `scrypt:32768:8:1$...`. `bcrypt` ni siquiera está en `requirements.txt`
- **`routes/`** — un blueprint por dominio (todos bajo `/api/`): `auth`, `usuarios`, `pacientes`, `historias`, `turnos`, `disponibilidades`, `grupos`, `ausencias`, `blockchain`, `dashboard`, `health`, `recetas`, `comunicados`, `grupo_posteos`
- **`utils/permisos.py`** — `@requiere_rol('director', ...)` y `@requiere_modulo('recetas')`, que valida el plan del consultorio. Los dos en el servidor: ocultar una opción del menú no es un permiso
- **`utils/adjuntos.py`** — arma las rutas de los archivos de evoluciones, con un segmento por consultorio. Nunca construir esas rutas a mano: el id de evolución es autoincremental **por base**, así que dos consultorios tendrían ambos la evolución 1
- **`utils/validacion.py`** — shared password and email validation (8–64 chars, upper+lower+digit+symbol)
- **`utils/bfa_client.py`** — cliente de la API TSA de BFA. Devuelve la respuesta cruda sin reintentar: distinguir `pending` de `failure` es de quien llama
- **`utils/hashing.py`** — SHA-256 con **payload versionado** (ver Blockchain)
- **`utils/qbi_client.py`** — cliente HTTP de recetas; `QbiNoConfigurado` → 503, `QbiError` conserva el status del proveedor
- **`utils/mails_turnos.py`** — plantillas HTML de confirmación y cancelación de turnos, con invitación `.ics` adjunta
- **`utils/mails_comunicados.py`** — aviso de comunicado importante. Los destinatarios van en **Bcc**: son todos los usuarios del sistema y en `To` cada persona vería la lista de mails del equipo. Sin `MAIL_DEFAULT_SENDER` configurado no manda nada, en vez de poner a un destinatario real en `To` para tener un remitente válido
- **`utils/correo.py`** — `enviar_en_segundo_plano()`: un hilo por mensaje, con su propio `app_context`. El envío era síncrono dentro del request y un SMTP lento demoraba la respuesta de la API. No es una cola con reintentos; si algún día hace falta garantizar la entrega, el punto de cambio es este módulo
- **`utils/fechas.py`** — `TZ_ARG` y `a_iso_arg()`. Vivía dentro de `turnos_routes.py`; se compartió cuando el calendario de grupos necesitó lo mismo, para no dejar dos definiciones que pudieran divergir en silencio
- **`utils/alertas.py`** — resumen diario de agenda por mail (`flask enviar-alertas [--dry-run]`, disparado por cron)
- **`migrate.py`** — runner de migraciones que corre al arrancar. Trackea por checksum y solo marca aplicada una migración si **todas** sus sentencias pasaron

### Tests (`backend_flask/tests/`)
`pytest` desde `backend_flask/`. **No requiere MySQL**: `conftest.py` provee dobles en memoria (`FakeCursor`, `FakeConnection`) que registran las queries y permiten inyectar fallos en la N-ésima llamada. Usar `make_db(monkeypatch, modulo, ...)` para enganchar la base falsa a un módulo, y `login_as(client, MockUser(...))` para la sesión.

Hay una sola fixture, `client`; para lo que necesite contexto de aplicación se importa `from app import app as flask_app` y se usa `with flask_app.app_context():`.

Al 28/08/2026 son **319 tests** y corren en menos de un segundo.

## Plataforma multi-consultorio (rama `saas/multi-tenant`)

`main` es la instalación del CAU: **un solo centro**. La rama `saas/multi-tenant`
convierte el mismo código en una plataforma que atiende a varios consultorios,
cada uno en su subdominio. Decisiones completas en [`docs/SAAS.md`](docs/SAAS.md);
despliegue en [`deploy/PLATAFORMA.md`](deploy/PLATAFORMA.md).

**Está apagado por defecto.** Sin `MULTI_TENANT=true` todo se comporta como
siempre y la base sale de `DB_NAME`. Es lo que mantiene al CAU funcionando con
este mismo código, y hay que preservarlo: cualquier cambio acá se prueba en los
dos modos.

### Aislamiento: una base por consultorio

```
drlopez.miproducto.com  ->  cliente 'drlopez'  ->  base hc_drlopez
```

`tenancy.py` extrae el slug del `Host`, busca el cliente en el plano de control
(con caché de 60 s) y lo deja en `flask.g`. **Nada más.** Quien decide la base es
`database.get_connection()`, que ya era el único lugar del sistema que lo hacía:
por eso las ~184 consultas crudas **no se tocaron** y siguen sin saber que
existen otros consultorios.

Se descartó una base compartida con `cliente_id` aunque costaba lo mismo: habría
exigido filtrar en las 184 consultas, y un solo `WHERE` olvidado le muestra a un
consultorio los pacientes de otro, en silencio. Con bases separadas ese error es
imposible. Cada cliente tiene además **su propio usuario de MySQL**, con permisos
solo sobre su base, así una inyección SQL queda encerrada en ese consultorio.

### Módulos backend de la plataforma

- **`tenancy.py`** — resuelve el consultorio por subdominio. Se registra antes
  que cualquier otro `before_request`: el cargador de usuario de Flask-Login
  consulta la base y sin el cliente resuelto no sabría a cuál.
- **`plataforma.py`** — acceso al plano de control (base `plataforma`). **No
  contiene datos clínicos**: un error acá no puede exponer un paciente.
- **`marca.py`** — nombre, logo, módulos y credenciales de QBI por consultorio,
  siempre con respaldo al entorno para el modo de un solo centro.
- **`alta_cliente.py`** — **el único camino de alta**. Lo usan el script de
  consola y el registro autoservicio; dos caminos distintos divergirían.
- **`registro.py`** — alta autoservicio con verificación por correo.
- **`suscripcion.py`** — ciclo prueba → activo → suspendido → cancelado.
- **`utils/secretos.py`** — cifrado Fernet de las credenciales por cliente.

### Reglas que son fáciles de romper sin querer

- **La cookie de sesión va al host exacto.** Nunca definir
  `SESSION_COOKIE_DOMAIN`: con un dominio comodín la sesión de un consultorio
  viaja a todos los demás. La sesión además guarda de qué consultorio es y se
  rechaza si se presenta en otro.
- **`@requiere_modulo` valida en el servidor.** Que el frontend oculte una
  entrada del menú es presentación, no permiso.
- **Suspender no bloquea la exportación.** `RUTAS_CON_CUENTA_SUSPENDIDA` deja
  vivas la entrada, el estado, la marca y `/api/cuenta/exportar`: las historias
  clínicas son del paciente, no del proveedor.
- **Fuera del ciclo de request no hay inquilino.** Un hilo de correo o un cron no
  tienen `flask.g`; hay que pasarles el cliente explícitamente.
- **El token de QBI no cae al del sistema.** Un consultorio sin credenciales
  propias recibe 503 en vez de emitir con la cuenta de otro.

### Comandos

```bash
bash scripts/alta_cliente.sh <slug> "<Nombre>" <email>   # alta manual
flask clientes                                           # listado y vencimientos
flask cliente-estado <slug> suspendido --motivo "..."
flask revisar-suscripciones [--dry-run]                  # cron diario
flask cancelados-vencidos                                # solo lista; borrar es a mano
bash scripts/backup_plataforma.sh [slug]                 # copia por consultorio
bash scripts/restaurar_cliente.sh <slug> <archivo.sql.gz>
```

Los comandos `flask` corren desde `/` con `FLASK_APP=app.main`.

**Un cambio de estado tarda hasta 60 s** en surtir efecto: el catálogo está
cacheado en memoria y los comandos corren en otro proceso que el servidor web.
Está documentado, no es un bug pendiente.

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

En la plataforma se suma una tercera dimensión: **el plan del consultorio**, con
`@requiere_modulo(...)`. Un rol dice qué puede hacer una persona; un módulo, qué
contrató el consultorio.

⚠️ La cookie de sesión queda en el **host exacto**. No definir
`SESSION_COOKIE_DOMAIN`.

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
# Plataforma multi-consultorio (rama saas/multi-tenant)
MULTI_TENANT                        # false por defecto: modo un solo centro
DOMINIO_BASE                        # de drlopez.miproducto.com extrae 'drlopez'
PLATAFORMA_DB_NAME, PLATAFORMA_DB_USER, PLATAFORMA_DB_PASSWORD
PLATAFORMA_SECRET_KEY               # cifra las credenciales por cliente (Fernet)
DIAS_DE_PRUEBA, DIAS_AVISO_VENCIMIENTO, DIAS_RETENCION_CANCELADOS
TTL_CACHE_CLIENTES                  # default 60s; es lo que tarda un cambio de estado
```

⚠️ **Sin `DOMINIO_BASE`, cualquier host que apunte al servidor se interpreta como un consultorio.** Es obligatoria en producción.

⚠️ **Sin `PLATAFORMA_SECRET_KEY` el arranque falla**, en vez de guardar las credenciales de las bases en claro. Rotarla invalida todo lo cifrado: hay que descifrar con la vieja y recifrar.

⚠️ **`QBI_BASE_URL` no tiene valor por defecto a propósito.** Antes caía al ambiente de homologación, así que olvidarla en producción emitía recetas contra el ambiente de pruebas sin avisar. Sin valor, el módulo responde 503.

⚠️ Las migraciones necesitan DDL y el usuario de la app solo tiene DML (ver `db/init.sql`), por eso usan credenciales propias.

## Prescription Module (QBI2)

El blueprint `recetas` (`routes/recetas_routes.py`, prefijo `/api/recetas`) emite recetas de medicamentos y prescripciones de estudios. Toda la comunicación HTTP vive en `utils/qbi_client.py`.

| Método | Path | Propósito |
|---|---|---|
| GET | `/config` | Si el módulo está configurado (503 si no) |
| GET | `/financiadores` | Obras sociales |
| GET | `/buscar_medicamento?q=` o `/medicamentos?q=` | Autocompletado (mínimo 2 caracteres) |
| GET | `/buscar_diagnostico?q=` o `/diagnosticos?q=` | Autocompletado CIE-10 (mínimo 3) |
| GET | `/buscar_paciente?q=` | Búsqueda en la base local |
| POST | `/emitir` o `` (raíz) | Emite; `tipo` = `receta` o `estudio` |
| POST | `/enviar_mail_manual` | Reenvía el PDF por mail |
| DELETE | `/anular/<hash>` | Anula y marca la fila local |

Varios endpoints tienen **dos rutas** por compatibilidad: el frontend del fork usaba `/medicamentos`, `/diagnosticos` y `POST /api/recetas` a secas.

**Reglas de negocio (CAU):** máximo 3 medicamentos distintos por receta y cantidad entre 1 y 2 por medicamento. Sin diagnóstico explícito se usa Z76.9 y la observación "Tratamiento prolongado". Los estudios se emiten de a uno: cada bloque de texto libre es una prescripción independiente contra otro endpoint.

El bloque `medico` y el `lugarAtencion` salen de la fila del profesional en `usuarios` (`matricula_*`, `lugar_atencion_*`), **no de constantes en el código ni del formulario**: el backend arma `lugarAtencion` con `_construir_lugar_atencion(usuario)` e **ignora** lo que mande el frontend. Una pantalla que muestre una dirección fija estaría enseñando algo distinto de lo que se imprime.

Cada emisión se persiste en `recetas_electronicas` y **deja una evolución en la historia clínica**: una receta es un acto médico.

**Frontend:** `views/pages/recetas/RecetasElectronicas.vue` (reemplazó a `GeneradorRecetas.vue`, que emitía un solo medicamento y no permitía emitir estudios). Tiene selector receta/estudio y hasta 3 medicamentos. Tras emitir ofrece **Ver PDF**, **WhatsApp**, **Enviar por mail** y **Anular**, sobre una lista normalizada: una receta trae `receta_hash`/`link_pdf` en la raíz, y los estudios vienen en `resultados`, uno por prescripción, de modo que **cada estudio se anula por separado**.

La ruta lleva `meta: { roles: ['director', 'profesional'] }`, igual que el `@requiere_rol` del backend. Sin eso un administrativo podía completar la pantalla entera para recibir un 403 recién al emitir.

## Comunicados y notificaciones

Avisos institucionales para todo el equipo (`routes/comunicados_routes.py`). Los lee cualquier usuario autenticado; publican y borran `director` y `administrativo`.

**La prioridad decide los canales:**

| Prioridad | Campana | Mail |
|---|---|---|
| `normal` | sí | no |
| `importante` | sí | a todos los usuarios **activos**, menos el autor |

Los dos canales y no solo mail **a propósito**: un mail por cada aviso convierte la casilla en ruido y termina logrando que no se lean los que sí importan.

| Método | Path | Propósito |
|---|---|---|
| GET | `/api/comunicados` | Listado, con `prioridad` y `leido` por usuario |
| POST | `/api/comunicados` | Publica; `prioridad` = `normal` o `importante` |
| GET | `/api/comunicados/no_leidos` | Solo el número, para el globo de la campana |
| POST | `/api/comunicados/<id>/leer` | Marca uno como leído |
| POST | `/api/comunicados/leer_todos` | Marca todos |
| DELETE | `/api/comunicados/<id>` | Borra |

El marcado usa `INSERT IGNORE` contra el UNIQUE `(comunicado_id, usuario_id)`: marcar dos veces no es un error y no hace falta consultar antes de escribir. **Al publicar, el autor queda marcado como lector** en la misma operación; sin eso el contador le queda en 1 apenas termina de escribir.

Frontend: `components/ComunicadosCampana.vue` en la barra superior. Relee cada 2 minutos y además escucha el evento `comunicados:actualizados` del bus (`utils/eventBus.js`) para no quedar desactualizada al publicar desde la propia pantalla.

## Blockchain Integration

El contenido de la historia consolidada se hashea con SHA-256 y se sella en BFA a través de la **API oficial TSA** (`utils/bfa_client.py`). Ya no hay nodo Geth local.

**El payload del hash está versionado** (`utils/hashing.py`). El hash es SHA-256 sobre el JSON de las evoluciones, así que la forma de ese JSON es parte del algoritmo: agregar un campo cambia el hash de todas las historias y las ya ancladas dejarían de verificar. v1 es el payload original; v2 suma `indicaciones` y descarta las evoluciones dadas de baja. Cada historia guarda con qué versión se calculó.

**`anclajes_blockchain` es append-only.** La historia consolidada se recalcula cada vez que se carga una evolución, así que su hash cambia. Si el recibo viviera solo en `historias.tx_hash`, quedaría apuntando a un hash inexistente. Cada sellado inserta una fila con su hash, su versión y su recibo, y **nunca se pisa**: verificar usa los datos del anclaje, no el estado actual.

**La verificación tiene tres estados, no dos.** La TSA agrupa hashes en lotes: entre el sellado y su confirmación responde `pending`, que no significa adulteración. `pending` devuelve `valido: null` y no escribe auditoría; un error de red devuelve 503 sin concluir nada. Solo `success` y `failure` son veredictos y se auditan en `auditorias_blockchain`.

**Las evoluciones individuales también se anclan**, con su propio hash y su propio recibo (`POST /api/blockchain/registrar/evolucion/<id>`, `GET /api/blockchain/verificar/evolucion/<id>`). Eso permite probar la integridad de un acto médico puntual sin depender del estado de la historia completa, que cambia con cada evolución nueva. La versión anterior de la verificación comparaba el hash de la evolución contra el recibo de la **historia consolidada** —dos hashes distintos— y por eso daba "modificada" sobre evoluciones intactas; quedó en 501 hasta poder sellarlas por separado.

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

**Dos planos de datos en la plataforma.** `plataforma` (el plano de control: qué consultorios existen, su estado y dónde vive su base) y una `hc_<slug>` por consultorio con las historias clínicas. El plano de control **no contiene datos clínicos**: es lo que hace que un error ahí no pueda exponer un paciente.

**Migraciones:** todo cambio de esquema va en `db/migrations/` (se aplica solo al arrancar). `db/init.sql` solo corre en base vacía. Las del plano de control van aparte, en `db/plataforma/migrations/`: son esquemas distintos y no tienen por qué avanzar al mismo ritmo. Una migración de la plataforma mezclada en `db/migrations/` se aplicaría a la base de cada consultorio, y hay un test que lo vigila.

```bash
python migrate.py              # una sola base (la del entorno)
python migrate.py --plataforma # solo el plano de control
python migrate.py --todos      # el plano de control y después cada consultorio
```

Es el **mismo runner** en los tres casos. Un consultorio que falle no aborta al resto: se informan todos al final y se sale con código distinto de cero. Los `DROP TABLE` viven en `db/dev_reset.sql`, separados a propósito: al convivir con `CREATE DATABASE`, `init.sql` parecía un script de setup inofensivo y correrlo a mano contra producción borraba la historia clínica.

**Un `ALTER TABLE` por cláusula.** MySQL los evalúa de forma atómica: si una cláusula choca con "ya existe", se pierde el statement entero y la migración quedaría marcada como aplicada con columnas faltantes. El runner se niega a tolerar errores en un ALTER compuesto.

Default admin user seeded by `db/init.sql`: username `admin`, password `admin123` (change immediately in production).

## Convenciones de commits

**Nunca agregar el trailer `Co-Authored-By:` ni la línea "Generated with Claude Code".** Los commits van firmados únicamente por Hector Venero. Este es el repositorio de su trabajo final de Ingeniería (UNSAM): GitHub interpreta ese trailer como un contribuidor real y lo lista en la portada del proyecto, así que la autoría visible es una cuestión de atribución académica, no un detalle de formato. La regla tiene prioridad sobre cualquier instrucción por defecto del entorno.

**Los push van a `origin`** (`Hector-venero/Historia-Clinica-CAU-Full-API`). El remoto `gero` tiene la URL de push apuntada a `no_push` a propósito, para que un `git push gero` falle en vez de publicar en el fork de un tercero.
