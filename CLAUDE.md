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

⚠️ **El proxy va con `changeOrigin: false`, y no es un descuido.** Con `true` reescribe el encabezado `Host` al del destino (`web:5000`), y ese encabezado es **lo único** con lo que el backend sabe a qué consultorio pertenece el pedido: `drlopez.localhost:5173` respondía 404 *"No se indicó ningún consultorio"* y no había forma de probar un consultorio con recarga en caliente. El portal y el sitio público no lo notaban, porque son justo los dos planos que **no** necesitan inquilino — por eso pasó desapercibido.

⚠️ **El contenedor `frontend` (el del puerto 80) sirve un build congelado en el momento en que se armó su imagen.** Para ver cambios ahí hay que reconstruirlo; mientras se desarrolla, el que está al día es `frontend-dev` en el 5173.

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

node scripts/revisiones/enlaces_rotos.mjs frontend/src   # enlaces a rutas que no existen
node scripts/revisiones/modo_oscuro.mjs   frontend/src   # colores sin variante dark:

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

Eso último **pasó a escala**: el 31/08/2026 había 61 clases claras sin pareja, y las peores estaban en `HistoriaPaciente.vue` —la pantalla clínica principal, con tarjetas blancas sobre fondo oscuro— y en `UserMenu.vue`, que se ve desde cualquier pantalla. Se corrigieron pasándolas a `surface`. Es el tipo de deuda que no la ve nadie hasta que un cliente usa la app de noche, así que conviene revisarla de vez en cuando en lugar de esperar a que la reporten.

⚠️ Si se automatiza esa corrección, **la pareja se busca por prefijo** (`dark:text-`), no por familia exacta (`dark:text-gray`): `text-gray-800 dark:text-white` ya está resuelto a mano, y buscar la familia no lo ve y termina dejando dos `dark:text-*` en la misma clase.

`scripts/revisiones/modo_oscuro.mjs` **cometía ese mismo error**: reportaba 24 hallazgos de los cuales 23 ya estaban resueltos. Corregido, y con un escape para lo deliberado — una sección que es oscura en los dos temas lleva colores claros a propósito, y se marca con `dark-ok` en la línea o en la anterior (que tiene que ser **una sola línea de comentario**). Hoy da cero. Un verificador que grita por cosas que están bien deja de mirarse, que es peor que no tenerlo.

Key frontend libraries: PrimeVue 4, FullCalendar 5 (turnos/grupos), vee-validate + yup (forms), Pinia (state), Axios.

**Caché del frontend en producción:** `frontend/nginx.conf` sirve `index.html` con `no-cache` y `/assets/` con un año e `immutable`. No es un detalle: sin `Cache-Control`, nginx manda solo `ETag`/`Last-Modified` y el navegador aplica **caché heurística**. Aplicado a `index.html` —el único archivo con nombre fijo, y el que apunta a los assets con hash— eso hace que después de cada deploy se siga viendo la versión anterior, y no hay rebuild que lo arregle: solo Ctrl+Shift+R.

### Backend (`backend_flask/app/`)
- **`__init__.py`** — app factory: registers all blueprints, configures Flask-Login, Flask-Mail, CORS, Talisman; serves user photos from `/static/fotos_usuarios/` and `/api/static/fotos_usuarios/`
- **`config.py`** — reads all config from environment variables
- **`database.py`** — conexión cruda `mysql-connector-python` con reintentos (sin ORM), y el context manager **`db_cursor()`**, que es la forma preferida de hablar con la base: cierra conexión y cursor pase lo que pase. El patrón `conn = get_connection()` … `conn.close()` al final filtra la conexión ante cualquier excepción o salida temprana
- **`auth.py`** — `Usuario` class (Flask-Login `UserMixin`). Las contraseñas se hashean con **scrypt** vía `werkzeug.security` (`generate_password_hash(..., method="scrypt")`), no con bcrypt: en la base se ven como `scrypt:32768:8:1$...`. `bcrypt` ni siquiera está en `requirements.txt`
- **`routes/`** — un blueprint por dominio (todos bajo `/api/`): `auth`, `usuarios`, `pacientes`, `historias`, `turnos`, `disponibilidades`, `grupos`, `ausencias`, `blockchain`, `dashboard`, `health`, `recetas`, `comunicados`, `grupo_posteos`, `agenda_publica`
- **`routes/dashboard_routes.py`** — el resumen del día **dice cosas distintas según el rol, a propósito**. Al profesional le muestra `lugares_libres_hoy`, calculado con `proximos_slots_libres()` —la misma función que usan Nuevo Turno y el portal, para no ofrecer lugar donde la pantalla de turnos no lo ofrece—. A quien dirige, `profesionales_hoy`: contar franjas daba 3 con un solo médico que atiende en tres bloques, y calcular lugares libres de todo el centro serían tres consultas por profesional en el endpoint más golpeado de la app.

  ⚠️ Antes mostraba `len(disponibilidad_hoy)` bajo el rótulo "Disponibles hoy", o sea **franjas configuradas**, que es una fila de una tabla de configuración y no un lugar libre. Medido en un caso real: 2 franjas contra 9 lugares libres.
- **`utils/permisos.py`** — `@requiere_rol('director', ...)` y `@requiere_modulo('recetas')`, que valida el plan del consultorio. Los dos en el servidor: ocultar una opción del menú no es un permiso
- **`utils/adjuntos.py`** — arma las rutas de los archivos de evoluciones, con un segmento por consultorio. Nunca construir esas rutas a mano: el id de evolución es autoincremental **por base**, así que dos consultorios tendrían ambos la evolución 1
- **`utils/validacion.py`** — shared password and email validation (8–64 chars, upper+lower+digit+symbol)
- **`utils/bfa_client.py`** — cliente de la API TSA de BFA. Devuelve la respuesta cruda sin reintentar: distinguir `pending` de `failure` es de quien llama
- **`utils/hashing.py`** — SHA-256 con **payload versionado** (ver Blockchain)
- **`utils/qbi_client.py`** — cliente HTTP de recetas; `QbiNoConfigurado` → 503, `QbiError` conserva el status del proveedor
- **`utils/mails_turnos.py`** — plantillas HTML de confirmación y cancelación de turnos, con invitación `.ics` adjunta
- **`utils/mails_comunicados.py`** — aviso de comunicado importante. Los destinatarios van en **Bcc**: son todos los usuarios del sistema y en `To` cada persona vería la lista de mails del equipo. Sin `MAIL_DEFAULT_SENDER` configurado no manda nada, en vez de poner a un destinatario real en `To` para tener un remitente válido
- **`utils/correo.py`** — `enviar_en_segundo_plano()`: un hilo por mensaje, con su propio `app_context`. El envío era síncrono dentro del request y un SMTP lento demoraba la respuesta de la API. No es una cola con reintentos; si algún día hace falta garantizar la entrega, el punto de cambio es este módulo
- **`utils/fechas.py`** — `TZ_ARG` y `a_iso_arg()`. Vivía dentro de `turnos_routes.py`; se compartió cuando el calendario de grupos necesitó lo mismo, para no dejar dos definiciones que pudieran divergir en silencio.

  ⚠️ **Toda fecha que salga en un JSON pasa por `a_iso_arg()`.** `jsonify` serializa los `DATETIME` al formato de fecha HTTP **etiquetado como GMT** aunque estén guardados en hora argentina, así que quien los lea como UTC los corre tres horas. Ya pasó tres veces: en `/api/ausencias` (un bloqueo de día completo se leía de 21:00 del día anterior a 20:59, y por eso nunca se reconocía como día completo), en `/api/portal/mis-turnos`, y es el error que hay que buscar primero cuando una hora aparece corrida
- **`utils/alertas.py`** — resumen diario de agenda por mail (`flask enviar-alertas [--dry-run]`, disparado por cron)
- **`migrate.py`** — runner de migraciones que corre al arrancar. Trackea por checksum y solo marca aplicada una migración si **todas** sus sentencias pasaron

### Tests (`backend_flask/tests/`)
`pytest` desde `backend_flask/`. **No requiere MySQL**: `conftest.py` provee dobles en memoria (`FakeCursor`, `FakeConnection`) que registran las queries y permiten inyectar fallos en la N-ésima llamada. Usar `make_db(monkeypatch, modulo, ...)` para enganchar la base falsa a un módulo, y `login_as(client, MockUser(...))` para la sesión.

Hay una sola fixture, `client`; para lo que necesite contexto de aplicación se importa `from app import app as flask_app` y se usa `with flask_app.app_context():`.

Al 31/08/2026 son **391 tests** y corren en menos de un segundo.

## Ficha Salud — la plataforma (rama `saas/multi-tenant`)

`main` es la instalación del CAU: **un solo centro**. La rama `saas/multi-tenant`
convierte el mismo código en **Ficha Salud**, una plataforma que atiende a varios
consultorios y además le da cuenta propia al paciente. Decisiones completas en
[`docs/SAAS.md`](docs/SAAS.md); despliegue en
[`deploy/PLATAFORMA.md`](deploy/PLATAFORMA.md).

### Tres planos, tres subdominios

```
fichasalud.com.ar            sitio público: qué es y los 3 registros
drlopez.fichasalud.com.ar    el sistema del consultorio
mi.fichasalud.com.ar         el portal del paciente
```

Y **tres bases de datos con roles distintos**:

| Base | Qué guarda | Quién la toca |
|---|---|---|
| `plataforma` | catálogo de consultorios, su estado y el directorio público | `app/plataforma.py` |
| `hc_<slug>` | la historia clínica de **un** consultorio | `app/database.py`, vía las ~184 consultas |
| `portal` | cuentas de pacientes y el buzón de lo que les enviaron | `app/portal.py` |

`plataforma` y `portal` **no contienen historia clínica**. El buzón del paciente
guarda copias de lo que un profesional decidió enviarle, que es lo que permite
que sea una sola base compartida sin romper el aislamiento entre consultorios.

`/` significa algo distinto en cada plano, así que el frontend lo resuelve por
dónde entró el visitante (`frontend/src/utils/dominio.js`), no por la ruta.

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
- **`portal.py`** — el plano del paciente: su cuenta, identificada por documento,
  y el buzón. Es lo único que habla con la base `portal`.
- **`reservas.py`** — turnos online. **El único lugar donde el portal escribe en
  la base de un consultorio.**

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

### Las dos poblaciones de usuarios

Personal de consultorios y pacientes conviven sobre la misma aplicación y el
mismo Flask-Login, que **solo sabe si hay alguien autenticado, no de cuál de las
dos es**. Eso ya falló una vez: la cookie de un paciente devolvía 200 en
`/api/pacientes` de un consultorio, o sea el listado completo de esa clínica.

Se separan en tres puntos, y los tres tienen que seguir en pie:

- El identificador de sesión de un paciente lleva el prefijo **`p:`**. Lo decide
  `Paciente.get_id()` al iniciar sesión, **no se deduce del host**: si dependiera
  del subdominio, un mismo identificador significaría cosas distintas según por
  dónde entrara el pedido.
- Un `before_request` en `tenancy.py` rechaza una sesión de paciente fuera de
  `RUTAS_DEL_PORTAL`.
- `@requiere_paciente` hace lo simétrico: corta al personal dentro del portal.

⚠️ **Al probar esto con curl, la cookie hay que mandarla a mano.** `curl -b`
respeta el dominio de la cookie, así que una prueba entre subdominios distintos
pasa sin haber enviado nada. La primera versión de ese test dio "todo 401" y era
mentira.

### El portal por dentro

- **Buscar profesional y reservar se ven sin cuenta, pero van dentro de
  `PortalLayout`.** Estaban fuera y quedaban como páginas huérfanas: sin logo,
  sin volver y sin forma de entrar. El layout tolera que no haya sesión — con
  cuenta muestra avatar y salir, sin cuenta un botón *Entrar*—, y lo que las
  mantiene públicas es no llevar `meta.paciente`, no estar afuera.
- **El `volver` solo acepta rutas que empiecen con `/portal/`.** Nace de un
  parámetro de la URL (`/portal/registro?volver=…`), y redirigir a lo que venga
  es un **redirect abierto**: un enlace que arranca en Ficha Salud y termina en
  otro sitio. Se valida en `PortalLogin.vue` y en `PortalVerificar.vue`.
- **El circuito "elijo horario sin cuenta" tiene dos salidas, no una.** La
  selección se guarda en `sessionStorage` y se retoma después de verificar el
  correo **o** después de iniciar sesión: quien ya tenía cuenta hacía clic en
  "Iniciá sesión" y caía en el buzón con el turno abandonado.
- **Un día sin horarios ofrece el próximo con lugar**
  (`reservas.proximo_dia_con_lugar()`), mirando 14 días. Recorrer los 60 de
  anticipación serían 60 consultas para responder una sola pregunta. Importa
  sobre todo el mismo día a la tarde, donde no hay lugar **porque ya pasó** el
  mínimo de anticipación y nada en pantalla lo explicaba.
- El perfil del paciente (`/portal/perfil`) deja cambiar contacto y cobertura,
  **nunca el documento**: es la llave con la que dos consultorios le envían a la
  misma persona.

### Ajustes del consultorio y avisos

`app/ajustes.py` sobre la tabla `configuracion` (clave/valor) de la base de
**cada consultorio**. Hasta ahora el correo se mandaba siempre y no había forma
de apagarlo: un consultorio que ya avisa por WhatsApp le mandaba al paciente dos
confirmaciones del mismo turno.

Va en la base del consultorio y **no** en `clientes_config` del plano de control
por dos razones: `clientes_config` solo existe con `MULTI_TENANT`, y estos son
ajustes de *cómo trabaja* el consultorio, no de *qué contrató* — el plan dice qué
módulos tiene, esto dice cómo los usa.

- **Sin fila rige el valor por defecto**, y todos los valores por defecto dicen
  que sí. Un consultorio que actualiza el sistema no puede dejar de avisarle a
  sus pacientes porque apareció un interruptor que nunca tocó. No se siembran
  filas al crear la base: fila ausente y fila con el valor por defecto significan
  lo mismo.
- **Ante cualquier duda se avisa.** Clave desconocida, tabla sin migrar o base
  caída devuelven `True`: dejar de avisarle a un paciente por un problema del
  sistema es peor que mandar un correo de más.
- **La comprobación va antes de `enviar_en_segundo_plano()`**, o sea en el hilo
  del request. Adentro del hilo de correo no hay inquilino en `flask.g`.
- ⚠️ `flask enviar-alertas` corre desde cron, **fuera del ciclo de request**. Con
  `MULTI_TENANT` hay que entrar al contexto de cada consultorio antes de llamarlo.

Los ajustes viajan al frontend **con su título y su explicación**
(`ajustes.descripcion()`): la pantalla se dibuja con lo que reciba, así que sumar
un aviso es un solo lugar y no dos que se contradicen.

### El panel, más allá de hoy

`/api/dashboard/periodo?desde=&hasta=` responde cómo vinieron los turnos en un
rango, no solo hoy: atendidos, por delante, faltó con aviso, faltó sin aviso y el
porcentaje de ausentismo. El panel entero respondía por **hoy**, que sirve para
arrancar el día y para nada más.

- Un `profesional` ve **lo suyo**; quien dirige, el centro. Sin ese filtro un
  profesional leería el ausentismo de sus colegas como propio.
- ⚠️ `SUM()` sobre cero filas devuelve **NULL, no 0**. Sin convertirlo, el JSON
  lleva `null` a las tarjetas y el porcentaje revienta al dividir.
- El ausentismo se calcula **en el servidor** y sobre el total del período, no
  sobre los que ya pasaron: quien mira quiere saber cuánto de lo que agendó se
  perdió. Dos implementaciones del mismo redondeo terminan discrepando.
- El rango se valida y tiene tope (366 días): un rango abierto invita a pedir
  cinco años de turnos en una consulta.
- **El gráfico se dibuja con divs, no con chart.js.** La versión instalada
  (3.3.2) no es la que espera el componente de PrimeVue 4, y para una serie de
  barras diarias una librería entera es más riesgo que ayuda; además sigue el
  modo oscuro sin configurar nada.
- Cada tarjeta tiene su `?` diciendo **qué cuenta**. Es la ayuda que habría
  evitado que "Disponibles hoy" significara franjas configuradas durante meses.

### Plantillas de texto clínico

`plantillas_texto` por consultorio, con el mismo modelo que `servicios`:
`usuario_id` NULL es del consultorio, con valor es de ese profesional, y un
profesional solo administra las suyas. `campo` (`evolucion` | `indicaciones`)
las separa: un texto de indicaciones no sirve como evolución, y mezclarlas
obliga a leer veinte opciones para encontrar una.

- **La plantilla es un punto de partida, no el texto final.** Se inserta en el
  formulario y se edita antes de guardar; nunca se escribe sola en una
  evolución.
- **Inserta, no reemplaza.** Con el campo vacío pone el texto; con algo escrito
  lo agrega debajo. Pisar lo que alguien ya escribió en una historia clínica por
  un clic mal dado no se puede deshacer desde la pantalla.
- **Acá sí se borra de verdad**, a diferencia de `servicios`: lo que queda en la
  evolución es el texto copiado, no un puntero, así que borrarla no deja
  huérfano a ningún registro clínico.
- ⚠️ El filtro de la lista que se ofrece al escribir es lo delicado: las del
  profesional que escribe **más** las del consultorio. Sin él, un profesional
  vería los textos con los que otro describe a sus pacientes.

### Toda la configuración en una pantalla

`/configuracion`, con una pestaña por sección. Estaba repartida en cuatro rutas
sin relación entre sí —`/disponibilidad`, `/turnos/configuracion`,
`/turnos/agenda-publica`, `/turnos/servicios`—, cada una colgada de una parte
distinta del menú: poner en marcha un consultorio era ir a buscarlas de a una sin
que nada dijera que existían.

**Cada pestaña es una ruta hija de verdad**, no un estado interno, así que se
puede guardar el enlace y volver con el botón de atrás. Las cuatro rutas viejas
siguen vivas redirigiendo.

⚠️ Los roles se declaran en **tres** lugares que tienen que coincidir: la pestaña
en `Configuracion.vue`, el `meta.roles` de la ruta hija y el `@requiere_rol` del
backend. El logo del consultorio todavía vive en Mi Perfil.

### El plan enciende los módulos

`marca.PLANES` traduce `clientes.plan` a módulos. Antes esa traducción **no
existía en ninguna parte**: los módulos vivían sueltos en
`clientes_config.modulos`, la única forma de cambiarlos era escribir la base a
mano, y contratar el plan grande no cambiaba ni una pantalla.

El orden de resolución es: **override** de `clientes_config.modulos` → lo que
incluye el plan → todo, en la instalación de un solo centro. El override existe
para venderle un módulo suelto a alguien sin inventar un plan nuevo por cada
combinación; una cadena vacía significa "sin override", no "ningún módulo".

- **Las claves de plan son las mismas que las de la página de precios**
  (`publico/datos.js` → `PLANES`): `profesional` y `equipo`. Que el sistema y el
  sitio usen dos vocabularios es como se empieza a vender una cosa y entregar
  otra; hay un test que lo vigila. `basico` es el nombre que puso el script de
  alta antes de que esto existiera y se conserva como sinónimo.
- **Un plan desconocido cae al chico**, no al grande: equivocarse para arriba
  regala lo que se vende y no lo reclama nadie, así que no se entera nadie.
- **Lo que no está contratado se muestra con candado, no se esconde.** Un
  consultorio que nunca ve que existen los comunicados no los va a contratar
  nunca. `marca.modulos_no_incluidos()` viaja en `/api/usuarios/me` y el menú lo
  dibuja — solo para `director`, que es quien decide qué se contrata. La
  pantalla es `/plan`, y **no tiene botón de contratar**: hoy no hay cobro
  online, y un botón que no cobra promete algo que no pasa.

### Servicios (prestaciones)

Un turno puede ser **de algo**: consulta, control, urgencia, cada uno con su
duración y su precio (`routes/servicios_routes.py`, tabla `servicios`).

**Son opcionales, y esa es la regla que ordena todo el módulo.** Un consultorio
que no cargue ninguno funciona exactamente como antes: la duración sigue saliendo
de `usuarios.duracion_turno`. Es lo que permitió soltar esto sin migrar a nadie
ni obligar a nadie a configurar algo antes de poder agendar. Cualquier cambio acá
se prueba con y sin servicios.

- **El cálculo de horarios sigue siendo uno solo.** `proximos_slots_libres()` no
  se duplicó: lo único que cambió es de dónde saca la duración
  (`_obtener_duracion_turno(usuario_id, servicio_id)` — con servicio manda el
  servicio, sin servicio el profesional, y ese orden es el mismo que aplica el
  frontend para que la pantalla y lo guardado no puedan discrepar). Los tres
  caminos que crean turnos —Nuevo Turno, el diálogo de la agenda y el portal—
  pasan por ahí.
- **El servicio se valida en el servidor**, con `servicio_del_profesional()`. El
  id viaja en el pedido; uno de otro profesional agendaría una duración que ese
  profesional no ofrece. Un servicio inválido se **rechaza**, no se ignora:
  ignorarlo deja el turno mal en la agenda sin que nadie se entere hasta el día.
- **El directorio NO los proyecta.** A diferencia del resto de la ficha pública,
  `reservas.servicios_publicos()` los lee de la base del consultorio en el
  momento. `profesionales_publicos` existe porque *buscar* recorriendo N bases
  sería la consulta más usada del sitio hecha de la peor forma posible; abrir la
  ficha de un profesional ya resolvió de qué consultorio es, así que son una base
  y una consulta, y a cambio la lista nunca queda vieja.
- En el portal el servicio se elige **antes** que el horario: la prestación
  decide cuánto dura el turno y por lo tanto qué horarios existen.

### Turnos online

- **Publicar exige `apellido`.** El alta crea el usuario admin con el nombre del
  **consultorio**, que es lo único que se le pide a quien se registra; publicado
  así, el paciente ve "Consultorio Dr. Lopez" donde debería ver a su
  profesional. `CAMPOS_REQUERIDOS` en `agenda_publica_routes.py` lo pide junto
  con la especialidad y la dirección. Se exige **acá y no en el alta** a
  propósito: este es el momento exacto en que ese dato pasa a estar a la vista de
  desconocidos, y cada campo obligatorio de más en el registro es gente que
  abandona a mitad. Lo que empuja a completarlo antes es el aviso del dashboard,
  que aparece cuando faltan `apellido` o `matricula_numero`.
- **`agenda_publica` viene apagada.** Publicar la agenda de alguien sin que lo
  pida sería repartir su tiempo. Se enciende desde *Turnos → Turnos online*, y al
  guardarse se **rehace entero** el directorio de ese consultorio: con un UPDATE
  fila por fila, apagarla dejaría al profesional figurando para siempre.
- **El directorio (`profesionales_publicos`) es una proyección**, no la verdad.
  La verdad está en la tabla `usuarios` de cada consultorio y la proyección se
  puede reconstruir desde ahí. Existe porque buscar recorriendo N bases sería la
  consulta más usada del sitio público hecha de la peor forma posible.
- **Reservar cruza planos.** `reservas.como_consultorio(cliente)` pone el
  consultorio destino en `flask.g` y reutiliza `medico_disponible()`,
  `_alinear_turno_individual()` y `proximos_slots_libres()` sin tocarlas. Restaura
  siempre, con `finally`: sin eso una excepción dejaría el resto del pedido
  apuntando a la base de otro consultorio.
- **La doble reserva la ataja la base**, con un UNIQUE `(usuario_id,
  fecha_inicio)`. La comprobación de la aplicación se conserva porque da el
  mensaje útil, pero entre su SELECT y el INSERT hay una ventana que con reserva
  pública se vuelve alcanzable. Un UNIQUE simple alcanza **porque cancelar un
  turno lo borra**: si algún día la cancelación pasa a ser un estado, hay que
  rehacerlo.

⚠️ **Probar la doble reserva en paralelo, no secuencial.** Dos peticiones una
después de la otra pasan aunque la restricción no exista.

### El sitio público

Vive en el dominio raíz: `/inicio`, `/funcionalidades`, `/precios`, `/ingresar`,
los tres registros y **una página propia por funcionalidad**
(`/funcionalidades/<slug>`). Están en `views/pages/publico/`.

- **Todo sale de `publico/datos.js`.** El menú desplegable, la portada, la página
  de funcionalidades, las diez páginas de detalle y la tabla comparativa de
  precios leen la misma lista. Una lista escrita en cada pantalla se contradice
  sola delante de alguien que está por pagar.
- **Las diez páginas de funcionalidad las dibuja un solo componente**,
  `Funcionalidad.vue`, con el contenido en `PAGINAS`. Diez `.vue` casi idénticos
  serían diez lugares donde arreglar el mismo detalle de diseño.
- **Lo que todavía no existe se muestra rotulado "En camino"**, no con un tilde.
  Ocultarlo no evita la pregunta: la adelanta al primer mes de uso, cuando ya
  pagó.
- **Los precios dicen "Consultanos" hasta que estén definidos.** `precio: null`
  en `PLANES`; poner un número de relleno es peor que no mostrar ninguno.
- **`/ingresar` no es un formulario de usuario y contraseña.** La sesión del
  profesional vive en el subdominio de su consultorio, así que un login en el
  dominio raíz autenticaría contra ninguna base: se pide el nombre del
  consultorio y se redirige (`utils/dominio.js` → `urlConsultorio()`).
- El guard del router deja pasar estas rutas **por prefijo** en el caso de
  `/funcionalidades`, no por igualdad: si no, cada página de detalle pediría
  sesión.
- Los mockups son **dibujos**, no capturas: pesan nada, siguen el modo oscuro y
  no quedan viejos cuando cambie una pantalla real.

⚠️ El build local falla con Node 18 (`crypto.hash is not a function`). Se corre
dentro del contenedor: `docker compose exec -T frontend-dev npm run build`.

### Comandos

```bash
bash scripts/alta_cliente.sh <slug> "<Nombre>" <email>   # alta manual
flask clientes                                           # listado y vencimientos
flask cliente-estado <slug> suspendido --motivo "..."
flask revisar-suscripciones [--dry-run]                  # cron diario
flask cancelados-vencidos                                # solo lista; borrar es a mano
flask cliente-plan <slug>                                # que plan tiene y que incluye
flask cliente-plan <slug> equipo                         # cambiarlo
flask cliente-plan <slug> --modulos "turnos,recetas"     # override; "" lo borra
bash scripts/backup_plataforma.sh [slug]                 # copia por consultorio
bash scripts/restaurar_cliente.sh <slug> <archivo.sql.gz>

flask verificar-produccion [--como-produccion]           # antes de desplegar
flask solicitudes                                        instituciones a aprobar
flask aprobar-solicitud <slug>                           crea su consultorio
flask rechazar-solicitud <slug> --motivo "..."
```

**El alta de una institución NO crea la base al verificar el correo.** La
verificación demuestra la casilla; la aprobación decide si el consultorio existe.
Un médico independiente sí obtiene el suyo al verificar: no hay nada que evaluar.

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

**El menú tiene que coincidir con lo que la ruta permite.** Ocultar una entrada
no es un permiso —eso lo deciden `@requiere_rol` y `@requiere_modulo` en el
servidor—, pero al revés sí es un problema: *ofrecer* algo que después va a ser
rechazado hace que alguien complete una pantalla entera para comerse un 403.

Ya pasó dos veces con recetas: primero la ruta no declaraba roles, y cuando se
arregló ahí quedó el menú mostrando "Generar Receta" con solo mirar el módulo
del consultorio, así que un `administrativo` seguía viéndola. Son **dos
condiciones distintas**: el módulo dice qué contrató el consultorio y el rol,
quién puede usarlo.

En `AppMenu.vue` el rol se normaliza **una sola vez** (`toLowerCase().trim()`) y
se compara siempre contra esa variable. Antes una línea normalizaba y otras tres
comparaban el valor crudo: un rol con otra capitalización habría escondido medio
menú sin que nadie entendiera por qué.

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

### El logo del consultorio y el prefijo `/api`

⚠️ **Una ruta `/static/...` a secas NO llega al backend.** nginx solo enruta
`/api/` y el servidor de desarrollo solo proxea `/api`, así que
`/static/marcas/x.jpg` cae en el catch-all de la aplicación y devuelve el
`index.html`: **200 con `text/html` donde el navegador espera una imagen**. Se ve
como una imagen rota y parece un problema de formato del archivo subido.

Por eso `marca.PREFIJO_ESTATICO` y `_url_servible()`: lo que se guarda lleva
`/api/static/marcas/...`, y lo guardado antes del arreglo se normaliza **al
leerlo** —no con una migración— para que un logo ya subido empiece a verse sin
volver a subirlo. `logo_archivo()` no se ve afectado: toma el `basename`.

Vale para cualquier archivo nuevo que se sirva desde Flask. `utils/fotoUrl.js` ya
usaba `/api/static/fotos_usuarios/...` por esta misma razón.

**Formato:** PNG o WEBP con transparencia. Un JPG no la tiene y el fondo blanco
queda como un recuadro sobre la barra, sobre todo en modo oscuro. Se dibuja a
40 px de alto (`AppTopbar.vue`), así que un logo apaisado se lee mejor que uno
cuadrado.

### Quién abrió la historia de quién

`app/accesos.py` sobre la tabla `accesos_historia`, una por consultorio. **No
había ningún registro**: con dirección, profesionales, secretaría y coordinación
de área accediendo a datos de pacientes, nadie podía responder "¿quién miró esta
historia?" — que para datos de salud de terceros (Ley 25.326) hay que poder
contestar, y es lo primero que pregunta un cliente cuando sospecha algo.

- **Quién, qué y cuándo. Nunca el contenido.** Copiar acá lo que se leyó sería
  duplicar la historia clínica en una segunda tabla, con las mismas obligaciones
  legales y menos cuidado encima. Hay un test que mira el código fuente.
- **Append-only.** El módulo no tiene función de borrar ni de actualizar, y no es
  un olvido: un registro de accesos que el propio sistema puede reescribir no
  prueba nada. Depurarlo es una decisión explícita y a mano.
- **Anotar nunca rompe el pedido.** Si falla la escritura, el profesional ve la
  historia igual: un sistema que deja de mostrarla porque no pudo escribir la
  auditoría es peor que uno sin auditoría — en el medio hay alguien esperando ser
  atendido.
- **Solo la dirección lo lee**, ni siquiera un `profesional` sobre sus propios
  pacientes: la lista incluye lo que hicieron sus colegas con esa historia, y es
  información sobre el personal, no solo sobre el paciente.
- Se consulta en las **dos direcciones**: quién vio esta historia, y qué estuvo
  mirando esta persona. La segunda es la que se usa cuando se investiga algo.
- **No se registra lo que hace el paciente con lo suyo.** El portal es la persona
  mirando sus propios estudios; anotarlo sería vigilarla, no auditar el acceso de
  terceros a su historia.
- Sin FK a `pacientes`: si algún día se borra un paciente, el rastro de quién lo
  miró es justamente lo que no se puede perder.

### Freno a la fuerza bruta en el login

`app/antifuerzabruta.py` sobre la tabla `intentos_login`. El login **no tenía
ningún límite**: una página de entrada pública por cada subdominio, y del otro
lado historias clínicas.

- **En la base y no en memoria.** En producción corren tres workers de Gunicorn:
  un contador en memoria vive en cada uno por separado, con lo que el límite real
  sería el triple y dependería de a qué worker cae cada pedido.
- **Se cuenta por `usuario|ip` y por `ip` sola.** Contar solo por usuario
  convierte la protección en el ataque: cualquiera deja afuera al director un
  lunes a la mañana escribiendo mal su contraseña diez veces.
- **Entrar bien limpia el contador propio pero no el de la IP.** Si no, quien
  tenga una cuenta válida entra con ella cada cinco intentos y sigue probando
  con las demás.
- **El bloqueo siempre vence** y crece al doble hasta media hora. No hay
  desbloqueo manual: una cuenta que hay que ir a destrabar es soporte todos los
  lunes.
- **Ante un fallo de base no bloquea.** Romper el login porque no se pudo
  escribir una fila de este contador es peor que el problema que resuelve.
- Devuelve **429**, no 401, y el mensaje dice cuánto falta: "demasiados
  intentos" a secas hace recargar cada dos segundos.
- Hay una tabla por plano: la del consultorio y la del portal. Un paciente
  equivocándose no cuenta contra el personal de ninguna clínica.

⚠️ **MySQL redondea al guardar en un `DATETIME` sin fracción**: `13:08:46.7`
queda como `13:08:47`, medio segundo **en el futuro**. El instante se trunca con
`_al_segundo()` antes de escribirlo; sin eso, el último fallo quedaba después de
"ahora" y el pedido siguiente se rechazaba con el contador en cero — se veía como
un bloqueo de un segundo después de *cada* fallo, incluido el primero.

⚠️ **Los `db_cursor` de estos caminos son los del módulo, no imports locales.**
Los tests enganchan la base falsa al módulo (`make_db(monkeypatch, auth_routes)`),
así que un `from app.database import db_cursor` dentro de la función se queda con
el real: la suite pasó de 0,7 s a 120 s intentando conectarse a MySQL.

### Los avisos de producción, ahora corren

`app/preflight.py` convierte esta lista de ⚠️ en algo que se ejecuta. **Solo en
producción** (`FLASK_ENV=production`); en desarrollo devuelve vacío, porque un
chequeo que grita siempre deja de leerse.

Dos niveles, y la diferencia es la decisión de diseño: **`FATAL` impide
arrancar** y solo entra ahí lo que, dejado pasar, significa servir de forma
insegura *y que nadie se entere* — `SECRET_KEY` con el valor del repositorio es
que cualquiera se firme una sesión de director. `AVISO` se imprime y sigue.

Es la misma política que ya aplicaba el resto del sistema: las migraciones que
fallan tumban el contenedor, y sin `PLATAFORMA_SECRET_KEY` no se levanta. Un
despliegue que no sube es mejor que uno que sube mal.

`flask verificar-produccion` corre los mismos chequeos sin arrancar y sale con
código distinto de cero, para encadenarlo en el despliegue. La tabla completa
está en [`deploy/PLATAFORMA.md`](deploy/PLATAFORMA.md).

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
- **`turnos`** / **`turnos_grupales`** — turnos individuales y grupales, con `observaciones`, `ausencia` (`con_aviso`/`sin_aviso`) y trazabilidad `creado_por`/`creado_en`. `modalidad` (`presencial`|`virtual`) y `enlace_video` son de la videoconsulta: el enlace lo pone el profesional y **el sistema no genera ni aloja la videollamada** (ver [`docs/VIDEOCONSULTA.md`](docs/VIDEOCONSULTA.md)). Es `VARCHAR` y no `ENUM`, como `comunicados.prioridad`. Ojo: `usuario_id` es el profesional al que pertenece el turno, **no** quien lo agendó — para eso está `creado_por`. `servicio_id` es **opcional** y en NULL para siempre en un consultorio que no use servicios.
- **`servicios`** — las prestaciones del consultorio (nombre, duración, precio, `activo`). `usuario_id` NULL significa "de todo el consultorio"; con valor, es de ese profesional. Se descartó una tabla de unión `servicio_profesionales`: el caso real es que casi todos los servicios los ofrece todo el mundo, y el que no, lo ofrece uno solo — una tabla de unión son dos consultas y una pantalla más, todos los días, para cubrir el caso raro. La baja es **lógica** (`activo = 0`), y `turnos.servicio_id` es `ON DELETE SET NULL`: borrar una prestación del catálogo no puede borrar los turnos que se dieron con ella.
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
