# Pendientes

Lo que está abierto al **31/08/2026**, con Ficha Salud (G1–G5) terminado, el
sitio público publicado, la videoconsulta funcionando y una pasada de arreglos
sobre lo que apareció al usar las pantallas de verdad. Cada punto trae cómo se detectó y cómo
reproducirlo, para no tener que volver a investigarlo desde cero.

**Acá va lo que NO está en la pasada de QA en curso.** Los trece hallazgos de
septiembre viven en [QA-2026-09.md](QA-2026-09.md), que es la lista viva mientras
esa pasada esté abierta; cuando se cierre, lo que quede sin resolver vuelve acá.
Tener las dos listas con lo mismo era la forma segura de que una quedara vieja
sin que nadie se enterara.

Un ítem tachado se borra **cuando su lección ya está en `CLAUDE.md` o
`SAAS.md`**. Ese es el criterio, y no "cuando pase un tiempo": mientras la
enseñanza viva solo acá, borrarlo la pierde. Varias veces la conclusión terminó
siendo distinta del reporte original, y esa corrección vale más que el ítem.

El registro de lo ya resuelto está en
[historico/MEJORAS-QA.md](historico/MEJORAS-QA.md) (los 15 problemas de la
pasada del 25/08) y en el historial de commits.

---

## 1. Rotar los secretos — depende de una acción fuera del repositorio

**Es lo único urgente.**

`SECRET_KEY`, `DB_PASSWORD`, dos `MAIL_PASSWORD` y `PRIVATE_KEY_BFA` quedaron
commiteados en el fork público de GeroGauna222. Borrarlos del HEAD no alcanza:
están en la historia de un repositorio que no controlamos.

**No es teórico.** Al verificar el envío de correo en segundo plano, el log
mostró la sesión SMTP completa: la credencial de Gmail **está activa y
funcionando**. Cualquiera con acceso al fork puede mandar correo desde la
casilla institucional.

Solo lo puede hacer Hector: hay que rotar las cinco en el proveedor
correspondiente y actualizar el `.env` de producción.

---

## 2. ~~Datos con doble codificación UTF-8 en la base~~ ✅ cerrado el 30/08/2026

**Corrección sobre el reporte original:** decía "es un problema de datos, no de
código", y era cierto, pero faltaba la causa —que es lo que impedía cerrarlo—.

`HEX(profesion)` del usuario `admin` daba `4D C383 C2A9 6469636F`: los bytes
UTF-8 de "MÃ©dico". La conexión de la aplicación ya negociaba `utf8mb4` y las
tablas también. **El único eslabón en latin1 era el cliente de MySQL que ejecuta
`db/init.sql` al crear el datadir**, que en el contenedor arranca en latin1 y
por lo tanto lee el archivo UTF-8 como si fuera latin1.

Por eso solo estaba afectada `hc_bfa`: los consultorios que se dan de alta con
`alta_cliente.py` escriben con mysql-connector y siempre estuvieron bien. Medido:
3 columnas de 1 fila. Nada de lo cargado desde la aplicación tenía el problema.

Se arregló por las dos puntas: `SET NAMES utf8mb4` en `init.sql` para que no
vuelva a pasar, y `20260901_reparar_doble_utf8.sql` para las filas ya escritas,
filtrando por `'Ã'` para que una fila correcta no se toque.

**Y apareció un segundo caso, peor.** `scripts/comparar_esquemas.sh` —que existe
justamente para esto— mostró que en las bases viejas
`pacientes.cert_discapacidad` no estaba definida como `ENUM('Sí','No')` sino como
`ENUM('SÃ­','No')`. No es un dato feo: es la **definición de la columna**, así
que guardar `'Sí'` no coincidía con ningún valor válido.
Lo corrige `20260901_enum_cert_discapacidad_utf8.sql`.

⚠️ Al aplicarlas quedó claro que **`migrate.py --todos` recorre los consultorios
del plano de control pero NO la base del entorno**: `hc_bfa` necesitó
`migrate.py` a secas. Con las dos bases conviviendo hay que correr los dos.

---

## 3. Antes de vender — depende de Hector, no del código

- **Verificar `fichasalud.com.ar`** y hacer una búsqueda en el INPI antes de
  fijar el nombre. Si no está libre, el cambio es barato: la marca está
  centralizada en `marca.py` y `stores/marca.js`.
- **Un correo de contacto del producto.** El pie del sitio muestra
  `hola@fichasalud.com.ar`, que todavía no existe. Está en una sola constante,
  `CORREO_CONTACTO` en `publico/SitioLayout.vue`.

El **logo**, los **precios** y los **términos y condiciones** también dependen de
Hector, pero están siendo tratados en la pasada de QA en curso —puntos 4, 11 y 9
de [QA-2026-09.md](QA-2026-09.md)— con lo que hay que hacer del lado del código
para recibirlos. No se repiten acá para no terminar con dos versiones.

---

## 4. Plataforma: lo que quedó sin verificar

La rama `saas/multi-tenant` está completa (F0–F8) pero hay cosas que **no se
pueden probar sin un dominio real**. Están anotadas acá para que nadie las dé por
verificadas.

- **DNS comodín y certificado.** `nginx/plataforma.conf.example` se validó con
  `nginx -t` dentro de la red de Docker —sintaxis y upstreams correctos— pero
  nadie probó todavía un `https://consultorio.dominio-real.com`. Let's Encrypt
  emite comodines **solo con desafío DNS-01**, no HTTP-01.

  Lo primero a comprobar cuando haya dominio: que el encabezado `Host` llegue
  intacto al backend. Es lo que decide a qué consultorio pertenece cada pedido.

- **Un cambio de estado tarda hasta 60 s.** El catálogo de clientes está cacheado
  en memoria (`TTL_CACHE_CLIENTES`) y los comandos de consola corren en otro
  proceso que el servidor web, así que su invalidación no lo alcanza. Medido:
  ~30 s. No se corrigió porque suspender por falta de pago no es una acción de
  emergencia; el punto de cambio sería `tenancy._cache`.

- **Migrar el CAU a la plataforma.** Se decidió dejarlo aparte: es la tesis y
  está en producción, no conviene que dependa de una arquitectura recién
  estrenada. Cuando la plataforma tenga rodaje se puede reconsiderar. Habría que
  migrar sus adjuntos a la estructura por consultorio (`scripts/migrar_adjuntos.sh`
  ya hace algo equivalente).

- **Legal — Ley 25.326.** Alojar datos de salud **de terceros** cae bajo la ley de
  datos sensibles. No cambia el código, pero sí el contrato y las condiciones del
  servicio. Conviene averiguar qué implica **antes** de facturarle al primer
  cliente.

- **El correo del portal no está probado con un SMTP real.** La verificación de
  cuenta de un paciente, la bienvenida y el aviso de documento nuevo se arman y
  se encolan, pero nadie vio llegar uno. Es lo primero a comprobar cuando haya
  credenciales de correo del producto (hoy las del `.env` son del CAU).

- ~~**El portal no tiene recuperación de contraseña.**~~ ✅ resuelto el
  02/09/2026. Con dos diferencias deliberadas respecto del circuito del personal,
  que conviene portar allá algún día: responde **lo mismo exista o no la
  cuenta** (el de `auth_routes.py` devuelve 404 y con eso delata qué correos
  están registrados) y manda el correo **en segundo plano** (allá es síncrono, y
  además un tiempo de respuesta distinto delata lo mismo que el mensaje único
  oculta). La sal del token es propia: sin eso, un enlace emitido para el
  personal serviría para cambiar la contraseña de un paciente.

- ~~**Nadie canceló un turno desde el portal.**~~ ✅ resuelto el 02/09/2026.

---

## 5. Menores

- ~~**Quedan 6 conexiones manuales en `turnos_routes.py`.**~~ ✅ hecho el
  30/08/2026, y con ellas las 20 que quedaban en todo el backend
  (`turnos_routes`, `grupos_routes`, `disponibilidades_routes`, más la carga del
  usuario en `__init__` y `auth`).

  Handler por handler y corriendo `pytest` después de cada archivo: el
  transformador automático ya había roto `turnos_routes` una vez.

  Dos cosas que aparecieron al convertir, y que conviene recordar:

  - En `crear_turno_grupal` y `editar_turno_grupal` el `try/except` tuvo que
    quedar **por fuera** del `with`. Con el `except` adentro, la excepción no
    atraviesa el context manager y **una tanda a medias se confirmaría igual**.
  - `api_turnos` y `editar_turno` abrían su conexión y después llamaban a
    `medico_disponible()`, que abre la suya: dos conexiones tomadas para un solo
    pedido. Ahora la comprobación va antes de abrir nada.

  Efecto lateral bienvenido: desaparecen los `except Exception -> 500` con
  `str(e)`, que devolvían el mensaje de MySQL al cliente.

- **Videoconsulta: hoy es un enlace, no video embebido.** Decisión tomada el
  30/08/2026 y explicada en [VIDEOCONSULTA.md](VIDEOCONSULTA.md). Lo que quedó
  fuera de alcance —Jitsi autoalojado, salas firmadas por turno, sala de
  espera— se reevalúa cuando un consultorio real use videoconsulta seguido, no
  antes. **Grabar consultas: no**, y eso no es un pendiente sino una decisión.

- **El correo de la videoconsulta no se vio llegar.** El bloque HTML, el botón y
  el `LOCATION` del `.ics` están verificados por unidad y contra el stack, pero
  el envío real depende del SMTP, que es el mismo pendiente de más arriba.

- **Quedan 26 clases claras sin variante `dark:`,** todas `text-gray-400`. Es un
  gris medio que se lee sobre los dos fondos, así que se dejaron. Las 35 que sí
  molestaban —tarjetas blancas en la historia clínica, el menú de usuario
  entero— se corrigieron el 31/08/2026.

  El chequeo quedó en `scripts/revisiones/` junto con el de enlaces rotos, así
  que se puede volver a correr en vez de tener que acordarse de mirar.

- **Node 20 en la máquina.** Vite 7 exige ≥ 20.19 y hay 18.19, así que
  `npm run dev` y `npm run build` locales fallan con `crypto.hash is not a
  function`. Mientras tanto se trabaja con el perfil `docker-compose.dev.yml`,
  que corre sobre `node:20-alpine`.
- **Prueba en navegador del flujo de autenticación.** El ciclo HTTP está
  verificado; falta recarga forzada, enlace directo a una ruta protegida y
  sesión vencida.

- **Usuarios de prueba en `drlopez`** (creados el 31/08/2026 **por la API**, no
  con SQL a mano, así pasan por la misma validación y el mismo hasheo):

  | Usuario | Contraseña | Rol |
  |---|---|---|
  | `admin` | `Prueba123!` | director |
  | `laura` | `Prueba123!` | profesional, con matrícula y agenda cargada |
  | `marta` | `Prueba123!` | administrativo |

  Existen **solo en la base local**. Sirven para lo que no se puede verificar con
  un único director: que el menú no ofrezca lo que el guard rechaza, y la métrica
  de lugares libres del dashboard. Con ellos se comprobó que `marta` recibe 403
  al emitir una receta, que era justo lo que el menú le seguía ofreciendo.

  ⚠️ `clinicasur` quedó con otra contraseña de admin y devuelve 401.
- **`ModuloRehabilitacion.vue`** (700 líneas, con su ruta) sigue solo en el fork.
  Se decidió no traerlo. Depende de `calendar-medical.css`, que sí está, así que
  portarlo es viable si alguna vez hace falta.
- **El directorio `bfa-node/` sigue en disco, y borrarlo es decisión del
  usuario.** El 30/08/2026 se sacó de git el único archivo versionado y se
  agregó `bfa-node/` al `.gitignore`, así que ya no forma parte del repositorio.
  Los archivos **no se borraron**: contienen material de una wallet y eso no es
  una decisión que corresponda tomar por cuenta propia.
  Quedó de cuando el anclaje usaba un nodo Geth local: no hay servicio ni código
  que lo use, solo comentarios que explican por qué se dejó de usar.

  **No se borró con el resto del código muerto porque no es código del
  repositorio.** De sus 127 archivos (4,8 MB) **solo uno está versionado**
  (`setup_bfa_node.sh`); el resto es un clon del repositorio de BFA más los
  datos del nodo, incluyendo directorios `keystore/` con permisos de root
  —creados por el contenedor de geth— y un `nucleo/password.txt`.

  Es decir: contiene **material de una wallet**, no está en git, y hace falta
  `sudo` para borrarlo. Si se elimina, no hay forma de recuperarlo. Conviene
  revisar antes si esa wallet tiene alguna dirección con saldo o identidad
  asociada al trabajo final.
