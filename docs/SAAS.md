# Plataforma SaaS para consultorios

Decisiones de arquitectura de la rama `saas/multi-tenant`. Están acá para no
volver a discutirlas: cada una tiene el motivo y el número que la respalda.

**Qué se busca:** vender el sistema como suscripción a consultorios chicos —un
odontólogo, un kinesiólogo, un consultorio de dos o tres personas— que no pueden
pagar un servidor propio ni quien lo mantenga. Referencia de mercado:
medicloud.com.ar.

**El CAU no se toca.** Sigue con su instalación de `main`. Esta rama construye
una plataforma nueva; migrar el CAU es una decisión posterior.

---

## Lo que se midió antes de decidir

| | |
|---|---|
| Tablas del esquema | **18**, ninguna con noción de cliente |
| Queries SQL crudas | **184** |
| Lugares donde se elige la base | **1** (`get_connection` en `app/database.py`) |
| Base vacía del sistema | **0,88 MB** |
| RAM del stack completo | ~510 MB (MySQL 387 + Flask 87 + nginx/frontend) |
| Marca "CAU/UNSAM" en el código | 28 menciones, 6 archivos, 3 logos |

Ese **1** es lo que hace viable el proyecto. Las 184 queries no saben a qué base
van: preguntan por una conexión y alguien se la da. Cambiar quién decide esa
conexión resuelve el aislamiento sin reescribir una sola consulta.

---

## Aislamiento: una base por cliente, aplicación compartida

Un solo backend y un solo frontend para todos. Al entrar un pedido, el
subdominio determina a qué base conectarse.

**Por qué no una base compartida con `cliente_id`:** costaría lo mismo —una base
vacía pesa 0,88 MB, así que la diferencia entre 50 bases y 50 conjuntos de filas
es despreciable— pero exigiría filtrar por cliente en las **184** queries. Un
solo `WHERE` olvidado le muestra a un consultorio los pacientes de otro, y el
error es silencioso: nadie avisa, se descubre cuando alguien ve un apellido que
no reconoce. Con bases separadas ese error es **imposible**: la conexión
físicamente no ve la otra base.

Se suma que cada cliente tiene **su propio usuario de MySQL**, con permisos solo
sobre su base. Así una inyección SQL en cualquier endpoint queda encerrada en ese
consultorio en lugar de exponer a todos.

Y lo operativo: backup, exportación y borrado por cliente son un `mysqldump` y un
`DROP DATABASE`. Con base compartida, "borrá todos mis datos" —que es un derecho
del cliente— se vuelve cirugía en 18 tablas.

**Por qué no una instancia completa por cliente:** cada una necesita su propio
MySQL (387 MB) más Flask (87 MB). En un VPS de 4 GB entran unos 6 clientes, y
actualizar a 30 son 30 despliegues. Con app compartida, esos 510 MB se pagan una
sola vez.

---

## El resto de las decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Producto | Genérico primero | El núcleo (turnos, pacientes, historia, recetas) ya sirve a casi cualquier consultorio. Los módulos por especialidad vienen después |
| Alta | Autoservicio desde el día uno | Se registra solo y en minutos tiene su sistema |
| Cobro | Prueba gratis, después manual | Transferencia o factura. Sin integración de pagos: es la parte más grande del trabajo y no valida nada del producto |
| Dirección | Subdominio por cliente | `consultoriolopez.<dominio>`. Es lo que le dice a `get_connection()` a qué base ir, sin que el usuario elija nada |
| Hosting | VPS propio, 4–8 GB | Alcanza para decenas de consultorios con esta arquitectura |
| Blockchain | Opcional, plan alto | "Tu historia clínica es inalterable" es un diferencial real, pero no algo que todo consultorio deba entender |
| Recetas QBI | Credenciales por cliente | Hoy el token es global del sistema; cada consultorio usa el suyo |
| Grupales y comunicados | Se conservan, ocultos por plan | Sirven a un centro con varios profesionales, no a quien trabaja solo |
| Marca | Configurable por cliente | Nombre y logo propios en la app, las recetas y los mails |

---

## Reglas que no se negocian

**Las cookies de sesión van al subdominio exacto**, nunca a `.<dominio>`. Una
cookie con dominio comodín viaja a todos los consultorios.

**Ocultar una opción del menú no es un permiso.** El backend valida los módulos
por plan igual que valida los roles: en el servidor. El frontend solo evita
mostrar lo que no corresponde.

**Suspender por falta de pago no borra datos.** Se corta el acceso, pero el
cliente tiene que poder exportar sus historias clínicas: son datos del paciente,
no del proveedor.

**Fuera del ciclo de request no hay inquilino.** Un hilo de correo o una tarea de
cron no tienen `flask.g`, así que hay que pasarles el cliente explícitamente.
`utils/correo.py` ya resuelve algo parecido con su propio `app_context`.

---

## Cómo se da de alta un consultorio

```bash
bash scripts/alta_cliente.sh drlopez "Consultorio Dr. Lopez" lopez@ejemplo.com
```

El script es un envoltorio de `backend_flask/app/alta_cliente.py`, que es lo que
después va a invocar el registro autoservicio: así no hay dos caminos de alta que
puedan divergir. Deja el consultorio listo e imprime la contraseña del admin una
sola vez.

Lo que hace, en orden:

1. Valida el subdominio (etiqueta DNS válida, mínimo 3 caracteres, no reservado).
2. Crea la base `hc_<slug>` y el usuario `c_<slug>` **con permisos solo sobre
   ella** — el usuario de MySQL admite 32 caracteres, de ahí el recorte.
3. Crea el esquema base a partir de `db/init.sql`, filtrando lo administrativo.
4. Aplica las migraciones con el mismo `migrate.py` del arranque normal.
5. Siembra el admin con una contraseña generada.
6. Registra el cliente en el plano de control, con la contraseña de su base
   cifrada.

Si algo falla a mitad, borra la base y el usuario que alcanzó a crear. Sin eso
quedaría una base huérfana: nadie la ve, nadie la limpia, y el slug parece libre
aunque la base ya exista.

**El esquema base sale de `db/init.sql`, no de una copia.** Dos definiciones del
mismo esquema divergen sin que nadie se entere — es justo lo que
`scripts/comparar_esquemas.sh` existe para detectar. Se descartan las sentencias
que crean la base del CAU, la seleccionan o dan de alta usuarios de MySQL, y
**también el `INSERT` del admin de desarrollo**: su contraseña (`admin123`) está
publicada en el README, y un consultorio nuevo no puede nacer con una cuenta de
credenciales conocidas.

### Verificado sobre el stack

Con dos consultorios de prueba dados de alta:

```
c_drgarcia -> hc_drlopez.usuarios     denied
c_drlopez  -> hc_bfa.pacientes        denied      (la base del CAU)
c_drlopez  -> plataforma.clientes     denied      (el plano de control)
c_drlopez  -> hc_drlopez.usuarios     OK
```

La contraseña de cada base queda cifrada en el plano de control (`gAAAAA…`) y la
aplicación la recupera al conectarse.

## Cómo se resuelve a qué base va cada pedido

```
drlopez.miproducto.com  ->  cliente 'drlopez'  ->  base hc_drlopez
```

`app/tenancy.py` extrae el slug del encabezado `Host`, busca el cliente en el
plano de control (con caché) y lo deja en `flask.g`. **Nada más.** Quien decide
la base es `database.get_connection()`, que ya era el único lugar del sistema que
lo decidía: por eso las 184 consultas no se tocaron.

Se registra antes que cualquier otro `before_request`, porque el cargador de
usuario de Flask-Login consulta la base y sin el cliente resuelto no sabría a
cuál.

**El modo está apagado por defecto** (`MULTI_TENANT=false`). Sin el interruptor,
todo se comporta como una instalación de un solo centro y la base sale de
`DB_NAME`: es lo que mantiene al CAU funcionando con este mismo código.

| Situación | Respuesta |
|---|---|
| `/api/health/` | 200 siempre — lo mira el monitoreo de la plataforma |
| Host sin subdominio | 404 |
| Consultorio inexistente | 404 (el mismo mensaje, para no poder enumerarlos) |
| Consultorio suspendido | 402, sin borrar datos |
| Sesión de otro consultorio | 401 |

### La sesión queda atada a su consultorio

La cookie va firmada con `SECRET_KEY`, que es de la plataforma y por lo tanto la
misma para todos, y adentro solo lleva el id del usuario. Como cada base tiene su
propio usuario 1, **una sesión de un consultorio autenticaba en otro**:
comprobado reenviando la cookie a mano, respondía 200 como el admin del otro.

En un navegador la cookie queda acotada al host y no viaja sola, pero eso es una
defensa del navegador, no del sistema: una cookie robada servía en todos los
consultorios, y bastaba con que alguien definiera `SESSION_COOKIE_DOMAIN` para
romper el aislamiento entero.

Ahora la sesión anota de qué consultorio es —vía la señal `user_logged_in`, para
que valga para cualquier camino de login presente o futuro— y se rechaza si no
coincide.

### Verificado sobre el stack

Dos consultorios, cada uno con un paciente **del mismo apellido**:

```
drlopez  busca "Perez" -> 1: ANA PEREZ    DNI 11111111
drgarcia busca "Perez" -> 1: CARLOS PEREZ DNI 22222222

cookie de drlopez -> drlopez.localhost   200
cookie de drlopez -> drgarcia.localhost  401
```

Y con `MULTI_TENANT=false`, el CAU sigue entrando por `localhost` como siempre.

## Pendiente legal

Alojar datos de salud de terceros en Argentina cae bajo la **Ley 25.326**
(datos sensibles). No cambia el código, pero sí el contrato y las condiciones del
servicio. Conviene averiguar qué implica antes de facturarle al primer cliente.
