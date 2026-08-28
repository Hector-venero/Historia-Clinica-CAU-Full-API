# Pendientes

Lo que está abierto al **28/08/2026**. Cada punto trae cómo se detectó y cómo
reproducirlo, para no tener que volver a investigarlo desde cero.

Los ítems tachados quedan un tiempo con la explicación de cómo se cerraron: en
varios casos la conclusión fue distinta del reporte original, y esa corrección
vale más que el ítem.

El registro de lo ya resuelto está en [MEJORAS-QA.md](MEJORAS-QA.md) (los 15
problemas de la pasada de QA del 25/08) y en el historial de commits.

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

## 2. ~~"Bloquear un día" en Agenda del profesional está roto~~ ✅ cerrado el 26/08/2026

**Corrección sobre el reporte original:** los dos errores eran reales
(mandaba `{fecha}` cuando la API pide `fecha_inicio`/`fecha_fin`, y la tabla
leía una columna `fecha` inexistente), pero `AgendaProfesional.vue` **no tenía
ruta, ni import, ni entrada de menú**. Era código inalcanzable: nadie podía
toparse con el bug.

Bloquear un día **sí funciona**, desde el modal del calendario en `Turnos.vue`,
que manda la forma correcta y contempla día completo y rango parcial.

El archivo se eliminó junto con el resto del código muerto.

---

## 3. ~~`/api/ausencias` miente sobre la zona horaria~~ ✅ resuelto el 26/08/2026

Devolvía los `DATETIME` con `jsonify` por defecto, que los serializa al formato
de fecha HTTP **etiquetado como GMT** aunque estén guardados en hora argentina,
y eso corría el valor tres horas en cualquier consumidor que lo leyera como UTC.

Se corrigió con `a_iso_arg()` al implementar el bloqueo de días en Nuevo Turno,
que era justamente lo que el bug rompía: un bloqueo de día completo se leía como
21:00 del día anterior a 20:59 y por lo tanto nunca se reconocía como día
completo. Verificado bajo `America/Argentina/Buenos_Aires`.

---

## 4. Datos con doble codificación UTF-8 en la base

`/api/usuarios/me` devuelve `"profesion": "MÃ©dico"` para el usuario `admin`:
es "Médico" codificado dos veces. Se va a imprimir mal en la receta, porque el
bloque `medico` sale de esa fila.

Es un problema de **datos**, no de código, pero conviene averiguar por dónde
entró antes de cargar usuarios de verdad: si hay una ruta de importación o un
formulario que guarda mal, cada usuario nuevo va a repetirlo. Revisar el charset
de la conexión y de la carga inicial.

---

## 5. Plataforma: lo que quedó sin verificar

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

---

## 6. Menores

- **`finally` en las conexiones de las rutas restantes.** Seis archivos de
  `routes/` siguen con el patrón manual `get_connection()` … `close()`. Cierran
  en todos los `return`, así que solo filtran ante una excepción. La forma
  preferida es `db_cursor()`.
- **Node 20 en la máquina.** Vite 7 exige ≥ 20.19 y hay 18.19, así que
  `npm run dev` y `npm run build` locales fallan con `crypto.hash is not a
  function`. Mientras tanto se trabaja con el perfil `docker-compose.dev.yml`,
  que corre sobre `node:20-alpine`.
- **Prueba en navegador del flujo de autenticación.** El ciclo HTTP está
  verificado; falta recarga forzada, enlace directo a una ruta protegida y
  sesión vencida.
- **`ModuloRehabilitacion.vue`** (700 líneas, con su ruta) sigue solo en el fork.
  Se decidió no traerlo. Depende de `calendar-medical.css`, que sí está, así que
  portarlo es viable si alguna vez hace falta.
- **El directorio `bfa-node/` sigue ahí, y borrarlo es decisión del usuario.**
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
