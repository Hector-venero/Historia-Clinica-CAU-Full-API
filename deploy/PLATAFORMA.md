# Desplegar la plataforma

Cómo poner en marcha la versión multi-consultorio en un VPS. Es distinto del
despliegue del CAU, que sigue siendo una instalación de un solo centro y no
cambia.

## Lo que hace falta

- Un VPS con Docker. **4 GB alcanzan para decenas de consultorios**: el stack
  entero ocupa ~510 MB y cada consultorio suma ~1 MB de esquema más sus datos.
- Un dominio propio.
- Un registro DNS **comodín**: `*.miproducto.com` → la IP del servidor. Es lo
  que hace que cada consultorio tenga su dirección sin tocar el DNS por cliente,
  y también lo que resuelve `mi.<dominio>`, el portal del paciente.

## Certificado

Let's Encrypt emite certificados comodín **solo con desafío DNS-01**, no con
HTTP-01: hay que probar el control del dominio, no el de una URL.

```bash
certbot certonly --manual --preferred-challenges=dns \
        -d miproducto.com -d '*.miproducto.com'
```

Con `--manual` hay que repetirlo cada 90 días, que es una forma segura de que un
día se venza sin que nadie se acuerde. Si el proveedor de DNS tiene plugin de
certbot, conviene usarlo y dejar la renovación automática.

## Puesta en marcha

```bash
cp env.example .env          # completar; ver más abajo
cp nginx/plataforma.conf.example nginx/plataforma.conf
sed -i 's/miproducto.com/TU-DOMINIO.com/g' nginx/plataforma.conf

export NGINX_CONF_FILE=./nginx/plataforma.conf
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

El arranque aplica las migraciones del plano de control y después las de cada
consultorio (`migrate.py --todos`). Si alguna falla, el contenedor no levanta.

### Antes de levantar: revisar la configuración

```bash
FLASK_APP=app.main flask verificar-produccion
```

Sale con código distinto de cero si hay algo que impide arrancar, así que se
puede encadenar en el script de despliegue. Son **los mismos chequeos que corren
al arrancar**, pero sin arrancar: se pueden correr contra el `.env` de producción
antes de levantar nada. Con `--como-produccion` los aplica aunque `FLASK_ENV`
todavía no lo sea, que es lo que sirve para probar el `.env` desde la máquina de
desarrollo.

**Lo que impide arrancar**, y por qué cada uno:

| | Qué pasa si se deja pasar |
|---|---|
| `SECRET_KEY` sin definir o con el valor de ejemplo | El valor de ejemplo está publicado en el repositorio: con él cualquiera se firma una cookie de sesión válida y entra como director de cualquier consultorio |
| `FLASK_DEBUG` encendido | El depurador de Werkzeug expone una consola de Python en el navegador ante cualquier excepción: es ejecución remota de código servida por la propia aplicación |
| `DOMINIO_BASE` vacío con `MULTI_TENANT=true` | Cualquier host que apunte al servidor se interpreta como el slug de un consultorio |
| `PLATAFORMA_SECRET_KEY` vacía | No se puede leer la credencial de ninguna base |
| `SESSION_COOKIE_DOMAIN` definida | Con un dominio comodín la sesión de un consultorio viaja a todos los demás |
| `FRONTEND_URL` sin `https://` | La cookie de sesión viaja en claro |
| `SESSION_COOKIE_SECURE` apagada a mano | Lo mismo, aunque el resto esté bien |

Lo demás —`MAIL_DEFAULT_SENDER`, `QBI_BASE_URL`, la contraseña de ejemplo de la
base, los endpoints de prueba de blockchain— **avisa y sigue**: puede ser una
decisión deliberada.

⚠️ La lista fatal es corta a propósito. Solo entra lo que, dejado pasar,
significa que el sistema está sirviendo de forma insegura **y nadie se va a
enterar**. Todo lo que un operador puede notar por su cuenta es un aviso.

### Variables que no pueden faltar

| Variable | Por qué |
|---|---|
| `MULTI_TENANT=true` | Sin esto se comporta como una instalación de un solo centro |
| `DOMINIO_BASE` | De `drlopez.miproducto.com` extrae `drlopez`. Sin definirlo, **cualquier** host que apunte al servidor se interpreta como un consultorio |
| `PLATAFORMA_SECRET_KEY` | Cifra las credenciales de cada base. Sin ella el arranque falla en lugar de guardarlas en claro |
| `PORTAL_DB_*` | El plano del paciente. Es **una sola base compartida**, a diferencia de las de los consultorios |
| `MYSQL_ROOT_PASSWORD` | Lo usan el alta de consultorios y los backups |
| `MAIL_*` | Sin remitente no salen ni la verificación del registro ni los avisos de vencimiento |

## Tareas programadas

```cron
# Avisos de vencimiento y suspensión de pruebas vencidas
0 8 * * *  cd /srv/plataforma && docker compose exec -T web sh -c 'cd / && FLASK_APP=app.main flask revisar-suscripciones'

# Copia de seguridad de todo
0 3 * * *  cd /srv/plataforma && bash scripts/backup_plataforma.sh
```

## Copias de seguridad

```bash
bash scripts/backup_plataforma.sh              # plano de control + cada consultorio
bash scripts/backup_plataforma.sh drlopez      # uno solo
```

Copia el plano de control, **el plano del paciente** y la base y los adjuntos de
cada consultorio.

El plano del paciente merece una nota: no es una base "de sistema" como el de
control. Guarda copias de estudios y recetas que **ya son del paciente**, y a
diferencia de la base de un consultorio, no hay otro lugar de donde recuperarlas.
Sus archivos (`uploads/_portal/`) entran en la misma copia.

Se hace **una copia por consultorio** y no un volcado de todo junto. Es la
ventaja concreta de tener una base por cliente: restaurar a uno solo no obliga a
tocar a los demás, que es exactamente lo que se necesita cuando alguien borra
algo por error un martes a la tarde.

Cada copia se verifica al generarla: que no esté vacía y que termine con
`Dump completed`. `mysqldump` puede salir con código 0 y dejar un volcado
truncado si se corta la conexión, y eso solo se descubre el día que hace falta.

### Restaurar

```bash
bash scripts/restaurar_cliente.sh drlopez /var/backups/plataforma/drlopez/drlopez_2026-08-29_03-00.sql.gz
```

Pide escribir el slug para confirmar, y la base la busca en el plano de control y
no en el nombre del archivo: un archivo se puede renombrar, y restaurar sobre la
base equivocada no tiene arreglo.

**Probado de punta a punta**: se borró el paciente de un consultorio, se
restauró desde la copia, el paciente volvió y los otros cuatro consultorios no
se tocaron.

Un backup que nunca se restauró no es un backup: es un archivo. Conviene repetir
esta prueba cada tanto sobre un consultorio de mentira.

## Lo que no está verificado

Todo lo de arriba corre y está probado **salvo el DNS comodín y el certificado**,
que necesitan un dominio real. La configuración de nginx sí se validó con
`nginx -t` dentro de la red de Docker: la sintaxis y los upstreams están bien,
pero nadie probó todavía un `https://consultorio.dominio-real.com`.

Cuando haya dominio, lo primero a comprobar es que el encabezado `Host` llegue
intacto al backend: es lo que decide a qué consultorio pertenece cada pedido.

```bash
curl -s https://drlopez.TU-DOMINIO.com/api/publico/marca
# tiene que devolver el nombre de ESE consultorio
```
