# Mejoras de la pasada de QA — resueltas

Los 15 problemas que salieron de la pasada de QA del 25/08/2026, posterior a la
reconciliación con el fork. **Los 15 están resueltos**, salvo el de rotación de
secretos, que depende de una acción fuera del repositorio.

**Estado al cerrar:** 210 tests verdes, 13 migraciones aplicadas desde base
vacía, 15 endpoints respondiendo, cero problemas de lint, cero vulnerabilidades,
y los dos caminos al esquema (init.sql y migraciones) produciendo el mismo
resultado.

---

## P0 — Bloqueaba un módulo entero

### 1. ✅ No se podían cargar los datos profesionales, y sin ellos no se emitía ninguna receta

El módulo exige apellido, DNI, matrícula y dirección de atención, pero el CRUD
de usuarios aceptaba solo 6 campos y no había un solo input de esos datos en el
frontend: las columnas solo se escribían con SQL a mano.

Se agregaron `PROFESSIONAL_FIELDS` y `_professional_values()` en el backend, y
los campos en el alta, la edición y **Mi Perfil** — esto último no existe en el
fork, donde solo los carga el director. Que cada profesional edite los suyos
tiene más sentido: es quien conoce su matrícula y dónde atiende.

Tres desviaciones deliberadas respecto del fork, que copiado tal cual dejaba el
problema a medias:

- **`apellido` se incluye.** El fork lo omite, pero la validación lo exige y
  solo se deduce del nombre como fallback: con un nombre de una sola palabra
  queda vacío y la receta se bloquea sin arreglo posible desde la app.
- **`sexo` acepta los cuatro valores del ENUM.** El fork valida solo F/M/X y
  convertía `'O'` a NULL en silencio.
- **`especialidad` se conserva para director**, no solo para profesional. Con la
  regla del fork, un director que prescribe iba sin especialidad en la receta.

**Verificado contra el proveedor real:** se creó un profesional con sus datos,
se emitió una receta que devolvió PDF, quedó persistida y dejó la evolución en
la historia clínica; después se editó la matrícula desde Mi Perfil y la receta
siguiente usó el dato nuevo.

De paso apareció que el proveedor también exige domicilio y DNI **del paciente**,
y respondía `QBI240 "debe ingresar calle y número"` sin decir de quién era el
domicilio. Ahora se valida antes y el mensaje dice qué falta y dónde cargarlo.

---

## P1 — Riesgo clínico

### 2. ✅ El turno se movía de horario y nadie se enteraba

El backend alinea el turno al siguiente slot: pedir las 10:10 guarda las 10:20.
Informaba el desplazamiento en `ajuste_horario`, pero ningún componente del
frontend leía ese campo, así que quien agenda le confirmaba al paciente un
horario y el sistema tenía otro.

`NuevoTurno.vue` muestra el aviso con ambos horarios y pide confirmarlo. Esa
vista además usaba `fetch()` crudo: se salteaba el interceptor de 401.

### 3. ✅ El rechazo por horario ocupado no ofrecía alternativas

Nuevo `proximos_slots_libres()`, que recorre las franjas del día salteando lo
ocupado. Los horarios van en la respuesta de error y el formulario los muestra
como botones que cargan el horario elegido.

Detalles que resuelve: alinea las sugerencias al slot (proponer uno que el
backend movería después sería contradictorio con el aviso anterior), no ofrece
horarios que no entren completos antes del cierre, recorre varias franjas si el
día está partido, y no sugiere nada si hay una ausencia que cubre el día.

**Verificado:** con 09:00–10:00 ocupado y franja hasta las 12:00, pedir las 09:10
devuelve 10:00, 10:20 y 10:40.

### 4. ✅ El envío de mail bloqueaba la respuesta

Era síncrono dentro del request. Se detectó porque la suite tardaba 8 segundos
esperando el timeout del correo en cada emisión.

Nuevo `utils/correo.py` con envío en un hilo con su propio contexto de
aplicación. **Medido:** crear un turno con paciente con email pasó de ~1 s a
**0.03 s**, y el envío se completa después.

### 5. ✅ Permiso de `administrativo` sobre disponibilidades

Confirmado: en el CAU son ellos quienes arman las agendas, así que conservan el
permiso de crear, editar y borrar.

---

## P2 — Deuda que molestaba

### 6. ✅ `historiaService.descargarPDF()` apuntaba a una ruta inexistente

Llamaba a `/historias/pdf` (plural) contra el `/historia/pdf` del backend: 404.
No rompía nada porque nadie usaba la función, pero era una trampa.

### 7. ✅ Fallback peligroso en la descarga de PDF

`HistoriaPaciente.vue` armaba la URL con
`import.meta.env.VITE_API_URL || 'http://localhost:5000'`. Sin esa variable
apunta al puerto del backend desde el navegador del usuario y sin el prefijo
`/api` — el mismo patrón que causó el downgrade HTTPS→HTTP en `axios.js`.

Ahora todo pasa por la instancia `api`. Se agregó `utils/descargas.js`: cada
vista lo resolvía por su cuenta y ninguna liberaba el object URL ni sacaba el
`<a>` del DOM. **Verificado:** `localhost:5000` ya no aparece en el bundle.

### 8. ✅ `npm run lint` reescribía archivos al ejecutarlo

Corría con `--fix`, así que ejecutarlo para *ver* errores reescribía ~20
archivos. Ya había provocado un conflicto con un `git stash` durante la
reconciliación. Separado en `lint` y `lint:fix`.

Al sacarle el `--fix` apareció lo que tapaba: **no eran 6 problemas sino 65**.
Los otros 59 se arreglaban solos en cada corrida y nadie los veía.

### 9. ✅ Variables muertas

Las 6 de `no-unused-vars` a mano, y los 59 de formato en un commit aparte,
registrado en `.git-blame-ignore-revs`.

### 10. ✅ Vulnerabilidades

De 3 a **0**: `brace-expansion`, `nanoid` y `js-yaml`. Cuando se escribió este
documento no había fix publicado.

---

## P3 — Deuda de fondo

### 11. ✅ Anclaje de evoluciones individuales

Estaba en 501: la implementación original comparaba el hash de la evolución
contra el recibo de la historia consolidada — dos hashes distintos, así que la
TSA respondía failure siempre y la pantalla decía "evolución modificada" sobre
evoluciones intactas.

Ahora cada evolución se sella por separado con su propio recibo, lo que permite
probar un acto médico puntual sin depender de la historia completa (que cambia
con cada evolución nueva). La tabla pasó a `anclajes_blockchain` porque aloja
los dos tipos.

Una evolución sin sellar responde `sin_anclaje`, no "modificada": no es lo mismo
no haber anclado que haber sido alterada.

**Verificado contra la TSA real:** los dos anclajes conviven con hashes y
recibos distintos, y cada verificación usa el suyo.

### 12. ✅ `usuarios_routes.py` sin conexiones manuales

Las 7 rutas restantes pasaron al context manager. El archivo ya no usa
`get_connection`.

**Corrección:** un análisis automático marcó 5 posibles fugas en otros archivos,
pero al revisarlas una por una **todas cierran en cada `return`**. Lo que sí les
falta es un `finally`, así que una excepción entre abrir y cerrar todavía filtra
— riesgo menor al corregido, anotado abajo.

### 13. ✅ Índices de búsqueda — medido, no hace falta tocarlo

Con 20.000 pacientes la búsqueda tarda **~90 ms**. El `EXPLAIN` confirma el full
scan (`type: ALL`, 19.558 filas), pero **un índice B-tree no puede ayudar con
`LIKE '%término%'`**: el comodín inicial lo inhabilita, y los índices de `dni`,
`nombre` y `apellido` ya existen sin ser usados por esta consulta.

Pasar los identificadores a búsqueda por prefijo sí usaría el índice
(`type: range`, 1000 filas), pero cambia el comportamiento: buscar "234" dejaría
de encontrar el DNI "1234567". A esta escala la diferencia no se mide.

### 14. ✅ `init.sql` y las migraciones podían divergir

`scripts/comparar_esquemas.sh` levanta dos bases y compara los dos caminos al
esquema. Compara columna por columna en orden alfabético, no el `CREATE TABLE`
crudo: una columna agregada al final por un `ALTER` figuraba como diferencia
solo por su posición, y ese ruido tapaba lo real.

**Encontró un tercer caso del mismo patrón**, después de `Domingo` y
`es_rehabilitacion`: `usuarios.apellido` y `usuarios.profesion` se habían
agregado a `init.sql` en el commit del módulo de recetas sin migración. En una
base anterior a ese commit no existen — y `apellido` es obligatoria para emitir.

**Comprobado que funciona:** agregando a propósito una columna solo a `init.sql`
la reporta; sin ella, los dos caminos coinciden.

---

## Único pendiente — fuera del repositorio

### 15. ⏳ Rotación de secretos

`SECRET_KEY`, `DB_PASSWORD`, dos `MAIL_PASSWORD` y `PRIVATE_KEY_BFA` quedaron
commiteados en el fork público. Borrarlos del HEAD no alcanza: están en la
historia de un repositorio que no controlamos.

Durante la verificación del envío de correo en segundo plano, el log mostró la
sesión SMTP completa: **la credencial de Gmail está activa y funcionando**.
Cualquiera con acceso a ese repositorio puede enviar correo desde la casilla
institucional. No es un riesgo teórico.

---

## Anotado para más adelante

- **`finally` en las conexiones restantes.** `ausencias_routes`,
  `disponibilidades_routes`, `turnos_routes`, `grupos_routes`, `auth_routes` y
  `dashboard_routes` cierran en cada `return`, pero una excepción entre abrir y
  cerrar filtra la conexión. `turnos_routes` es el más grande (17 sitios).
- **Node 20 para desarrollo local.** Vite 7 lo exige; con Node 18 el build falla
  con `crypto.hash is not a function`. En Docker no cambia nada.
- **Prueba en navegador del flujo de autenticación.** El ciclo HTTP está
  verificado (401 → login → rol desde la cookie → logout → 401), pero no el
  hard-reload, el deep-link a ruta protegida ni la sesión expirada.
