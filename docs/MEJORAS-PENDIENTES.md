# Mejoras pendientes

Resultado de la pasada de QA del 25/08/2026, después de terminar la
reconciliación con el fork. Los ítems están ordenados por impacto, no por
esfuerzo.

**Estado base:** 157 tests verdes, 11 migraciones aplicadas desde base vacía,
14 endpoints respondiendo, sellado y verificación contra la TSA real de BFA
funcionando. Nada de lo de abajo impide que el sistema funcione, salvo el P0.

---

## P0 — Bloquea el uso de un módulo entero

### 1. No hay forma de cargar los datos profesionales, y sin ellos no se puede emitir ninguna receta

El módulo de recetas exige, para emitir:

- `medico.nombre`, `medico.apellido`, `medico.nroDoc` (DNI)
- `matricula.numero`
- `lugarAtencion.domicilio.direccion`

Pero el CRUD de usuarios solo acepta `nombre`, `username`, `email`, `password`,
`rol` y `especialidad`. El perfil propio solo acepta `nombre`, `email` y foto.
**Las columnas `apellido`, `dni`, `sexo`, `telefono`, `matricula_*` y
`lugar_atencion_*` solo se pueden escribir con SQL a mano.**

Verificado: emitir una receta con el usuario admin devuelve
`400 "Complete la dirección del lugar de atención en su perfil."`, y no hay
ninguna pantalla donde completarla.

**Ya está resuelto en el fork** — se me pasó al portar recetas en F7, porque
miré el módulo de recetas y no de dónde salían sus datos. Hay que traer:

| Qué | De dónde |
|---|---|
| `_professional_values()` y `PROFESSIONAL_FIELDS` | `gero/main:backend_flask/app/routes/usuarios_routes.py` |
| Campos en el alta de usuario | `gero/main:frontend/src/views/pages/usuarios/CrearUsuario.vue` |
| Campos en la edición | `gero/main:frontend/src/views/pages/usuarios/EditarUsuario.vue` |

Al portarlo, revisar dos cosas: que el ENUM de `sexo` que valida sea
`('M','F','X','O')` (el del fork valida `('F','M','X')` y descartaría `'O'`), y
que `matricula_tipo` acepte `'OP'`.

Conviene además exponerlo en **Mi Perfil**, no solo en el alta por director: es
el profesional quien conoce su matrícula y dónde atiende.

---

## P1 — Riesgo clínico o de datos

### 2. El turno se mueve de horario y nadie se entera

`_alinear_turno_individual()` redondea el turno hacia arriba al siguiente slot.
Pedir las **10:10** guarda las **10:20**. El backend informa el desplazamiento
en `ajuste_horario`, pero **ningún componente del frontend lee ese campo**
(verificado con grep sobre todo `frontend/src`).

Consecuencia: quien agenda le dice al paciente "10:10" y el sistema tiene
"10:20". En una agenda médica eso es una persona esperando en la sala.

Arreglo: mostrar un aviso cuando la respuesta trae `ajuste_horario`, en
`NuevoTurno.vue` y en `Turnos.vue`.

### 3. Pedir un horario ocupado da un error sin salida

Encadenado con lo anterior: si el slot alineado está tomado, la respuesta es
`400 "El profesional no esta disponible en esa fecha u horario"` — sin decir
cuándo sí hay lugar. Verificado: con un turno en 10:00–10:20, pedir las 10:05
alinea a 10:20, lo encuentra ocupado y rechaza, aunque 10:40 esté libre.

Arreglo mínimo: que el error incluya los próximos slots disponibles de ese día.

### 4. El envío de mail es síncrono dentro del request

Tanto la emisión de recetas como la confirmación de turnos mandan el mail
dentro del request. Si el SMTP está lento, la respuesta de la API se demora lo
mismo. Se detectó porque la suite de tests tardaba 8 segundos: cada emisión
exitosa esperaba el timeout del servidor de correo.

Los helpers ya no propagan la excepción (un mail fallido no invalida la receta
ni el turno), pero el tiempo se sigue pagando. Conviene una cola simple o un
hilo aparte.

### 5. Confirmar la ampliación de permisos de `administrativo`

En F9 el rol `administrativo` pasó a poder **crear, editar y borrar**
disponibilidades; antes solo podía verlas. Se hizo porque la asimetría
lectura/escritura era rara y `CLAUDE.md` dice que ese rol se ocupa de la agenda.

Es una decisión de negocio, no técnica. Si no es lo que se busca, es sacar
`'administrativo'` de tres `@requiere_rol` en `disponibilidades_routes.py`.

---

## P2 — Deuda que va a molestar

### 6. `historiaService.descargarPDF()` apunta a una ruta que no existe

Llama a `/pacientes/{id}/historias/pdf` (plural) y el backend expone
`/pacientes/{id}/historia/pdf` (singular). Verificado: 404 contra 200.

Hoy no rompe nada porque **la función no se usa**: las vistas descargan el PDF
con `window.open()` y la ruta correcta. Pero es una trampa para el próximo que
la llame. Corregir el path o borrar la función.

### 7. Fallback de URL peligroso en la descarga de PDF

`HistoriaPaciente.vue` líneas 148 y 156:

```js
const base = import.meta.env.VITE_API_URL || 'http://localhost:5000';
```

Si `VITE_API_URL` no está en el build, arma `http://localhost:5000/pacientes/…`
— sin el prefijo `/api` y apuntando al puerto del backend desde el navegador del
usuario. Hoy funciona porque el compose pasa `VITE_API_URL=/api`, pero es el
mismo patrón que ya causó el downgrade HTTPS→HTTP en `axios.js`. Usar la
instancia `api` como el resto del código.

### 8. `npm run lint` corre con `--fix` y modifica archivos

El script es `eslint --fix .`, así que ejecutarlo para *ver* errores termina
reescribiendo ~20 archivos (reordena `<script setup>` antes de `<template>`).
Esto ya provocó un conflicto con un `git stash` durante la reconciliación.

Arreglo: `"lint": "eslint ."` y `"lint:fix": "eslint --fix ."`.

### 9. Seis errores de lint preexistentes

Todos variables sin usar, en `AppConfigurator.vue`, `formatDate.js`,
`Turnos.vue` y `ConfiguracionTurnos.vue`. Ruido que tapa errores nuevos.

### 10. Quedan 3 vulnerabilidades altas

`brace-expansion`, `js-yaml` y `nanoid`, todas transitivas y sin fix disponible
en las dependencias directas. Revisar cuando publiquen.

---

## P3 — Mejoras de fondo

### 11. Anclaje de evoluciones individuales

`/api/blockchain/verificar/evolucion/<id>` responde **501**. La implementación
anterior comparaba el hash de la evolución contra el recibo de la historia
consolidada — dos hashes distintos — así que nunca podía dar válido y mostraba
"evolución modificada" sobre evoluciones intactas.

Implementarlo bien requiere sellar cada evolución por separado y guardar su
propio recibo. Las columnas ya existen (`evoluciones.hash_local`, `tx_hash`,
`estado_bfa`, `fecha_anclaje_bfa`) y `anclajes_historia` se puede extender con
`entidad_tipo`.

### 12. Fugas de conexión que quedaron sin convertir

`db_cursor()` se aplicó a pacientes, turnos (`editar_turno`), historias,
blockchain, dashboard, recetas, comunicados, posteos, alertas y perfil. **Falta
`usuarios_routes.py`**, que tiene varios `return` tempranos sin cerrar la
conexión (por ejemplo en el alta cuando el username ya existe, y en la edición
en cada validación). Mismo patrón que ya se corrigió en otros seis archivos.

### 13. Sin índice en las búsquedas de pacientes

`buscar_pacientes` hace `LIKE '%término%'` sobre `dni`, `nombre`, `apellido` y
`nro_hc`. Con comodín inicial no se usa índice: es un full scan por búsqueda.
Con pocos pacientes no se nota; conviene medirlo antes de que crezca.

### 14. `db/init.sql` y `db/migrations/` pueden divergir

Hoy no hay nada que verifique que una base creada desde `init.sql` quede igual a
una construida aplicando migraciones. Ya pasó dos veces que una columna se
agregara solo a `init.sql` (`disponibilidades.Domingo`,
`grupos_profesionales.es_rehabilitacion`), y ambas rompieron en runtime con 1265
y 1054.

Durante F10 hice esa comparación a mano con un script. Vale la pena dejarlo como
test: levantar las dos bases y diffear `mysqldump --no-data`.

### 15. Rotación de secretos

Único ítem de la fase 0 que sigue abierto. En el fork público quedaron
commiteados `SECRET_KEY`, `DB_PASSWORD`, dos `MAIL_PASSWORD` y
`PRIVATE_KEY_BFA`. Borrarlos del HEAD no alcanza: están en la historia de un
repositorio que no controlamos.

---

## Verificado que funciona (no tocar sin motivo)

- **Sellado y verificación en BFA reales.** Se selló un hash contra la API TSA y
  devolvió recibo. La verificación respondió `pending` con `valido: null` y
  **no escribió auditoría** — con el código anterior habría dicho "la historia
  fue modificada" y lo habría dejado escrito en la tabla legal.
- **`anclajes_historia` es append-only.** Tras cargar una segunda evolución, el
  hash de la historia cambió pero el anclaje conservó el suyo y su recibo, y la
  verificación siguió usando el del anclaje.
- **Soft-delete corta la sesión.** Dar de baja a un usuario con sesión abierta
  la invalida al instante (401) y le impide volver a entrar.
- **RBAC.** Un profesional recibe 403 en `/api/usuarios`,
  `/api/blockchain/auditorias`, `/api/health/secure` y al publicar comunicados.
- **Solape de turnos.** Un turno superpuesto se desplaza al siguiente slot libre
  o se rechaza; no se duplica.
- **PDFs.** Historia completa y evolución individual generan PDF válido con el
  contenido correcto.
- **Migraciones.** 11 aplicadas desde base vacía, sin errores.

---

## Corregido durante esta pasada

- Los PDF mostraban **`Cobertura: None`**. `paciente.get('cobertura', '-')` solo
  usa el default si falta la clave, pero la clave existe con valor `None`. Los
  campos `fecha_nacimiento` y `sexo` ya tenían el `or '-'`; a `cobertura` se le
  había pasado por alto, en las dos rutas de PDF.
