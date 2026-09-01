# Reconciliación con el fork de GeroGauna222

Registro de qué se trajo del fork, qué se dejó afuera y qué se cambió al
traerlo. Sirve para no volver a discutir decisiones ya tomadas y para saber
dónde mirar si algo del fork hace falta más adelante.

**Contexto:** un compañero forkeó el repositorio y trabajó por su cuenta,
acumulando 28 commits. El fork **no** recibe cambios de vuelta: el remoto `gero`
tiene la URL de push puesta en `no_push` a propósito.

Estados preservados en tags:

| Tag | Qué es |
|---|---|
| `archivo/fork-gerogauna` | último commit del fork tal como se recibió |
| `archivo/pre-reconciliacion-main` | `main` antes de reconciliar |
| `archivo/refactor-bfa-tsa` | la rama `refactor/bfa-tsa-api` antes de reconciliar |

Para comparar contra el fork sin traer nada:

```bash
git show archivo/fork-gerogauna:frontend/src/views/pages/turnos/ModuloRehabilitacion.vue
git diff --stat archivo/fork-gerogauna HEAD -- frontend/src
```

---

## Fase 1 — Reconciliación de los 28 commits (24/08–25/08/2026)

Trece fases (F0–F12). Trajo el backend de turnos, el módulo de recetas, los
comunicados, los grupos y el runner de migraciones, y corrigió en el camino la
verificación de blockchain, los anclajes append-only y el hash versionado.

El detalle de lo que salió de la pasada de QA posterior está en
[historico/MEJORAS-QA.md](historico/MEJORAS-QA.md).

**Lo que esa fase dejó afuera sin querer:** el frontend del calendario. Se llevó
`turnos_routes.py` pero `Turnos.vue` y `CalendarioGrupo.vue` quedaron en la
versión vieja — en toda la reconciliación solo los tocaron los commits de
formato. Se resolvió en la fase 2.

---

## Fase 2 — Portes de interfaz (26/08/2026)

### Calendario y agenda ✅ traído

|  | Antes | Después |
|---|---|---|
| `Turnos.vue` | 431 líneas | 1027 |
| `CalendarioGrupo.vue` | 248 | 806 |
| `calendar-medical.css` | no existía | 361 |

No era solo estético. Trajo el contador de ausencias del paciente dentro del
modal del turno, el modal de bloqueo de agenda y el alta de turno en línea —
todo contra endpoints que **el backend ya exponía y el calendario no usaba**.

También trajo el aviso de `ajuste_horario` en los tres caminos que crean o
mueven un turno, incluido arrastrar y soltar. Eso **corrigió a medias un arreglo
anterior**: el aviso se había agregado solo en `NuevoTurno.vue`, así que mover
un turno en el calendario seguía corriendo el horario en silencio.

**Se agregó al backend** `GET /api/grupos/<id>/ausencias`, el único endpoint que
el frontend del fork necesitaba y que no existía. Se escribió con `db_cursor()`
en vez del `get_connection()` manual del original.

### Pantalla de recetas ✅ traída, con injertos

`recetas/RecetasElectronicas.vue` reemplazó a `GeneradorRecetas.vue`. La
anterior **no mencionaba la palabra "estudio" ni una vez**: el backend los
soporta desde mayo y no había forma de emitirlos. Además armaba el payload con
un solo medicamento, cuando la regla del CAU permite tres.

Reemplazarla tal cual habría sido un retroceso, porque la del fork solo ofrece
"Abrir PDF". **Se le injertaron las cuatro acciones** que ya existían: ver PDF,
WhatsApp, enviar por mail y anular.

Tres correcciones sobre lo que traía el fork:

- **El lugar de atención estaba hardcodeado** ("CAU UNSAM", Av. 25 de Mayo
  1169). El backend lo arma desde la fila del profesional e ignora el
  formulario, así que no cambiaba la receta emitida, pero mostraba en pantalla
  una dirección distinta de la que se imprime.
- **La ruta no tenía `meta.roles`.** El backend exige director o profesional, de
  modo que un administrativo completaba la pantalla entera para recibir un 403
  recién al emitir.
- **`stores/user.js` descartaba los campos profesionales.** La pantalla lee
  `dni`, `matricula_*` y `lugar_atencion_*`; `/api/usuarios/me` ya los devolvía
  y `setUser` los tiraba, con lo que el botón Emitir **nunca se habilitaba**.
  Copiar los archivos sin más habría dado una pantalla linda que no emitía nada.

### Módulo de rehabilitación ❌ no traído

`ModuloRehabilitacion.vue`, 700 líneas y con su ruta en el router del fork.
Decisión del usuario. Depende de `calendar-medical.css`, que sí está, así que
portarlo después es viable.

### Notificaciones de comunicados ⚠️ desarrollo nuevo

**No existían en ninguna de las dos ramas.** La impresión de que el fork las
tenía era incorrecta: `comunicados_routes.py` no manda un solo mail ni genera
ninguna notificación en ninguna de las dos versiones, y `Comunicados.vue`
difiere entre ambas en **una línea**.

Se implementaron de cero: prioridad `normal`/`importante`, campana en la barra
superior y mail solo para los importantes. Ver la sección "Comunicados y
notificaciones" en `CLAUDE.md`.

---

## Cosas que el fork hacía distinto y se conservaron a propósito

- **`Mi Perfil` edita los campos profesionales.** En el fork solo los carga el
  director. Que cada profesional edite los suyos tiene más sentido: es quien
  conoce su matrícula y dónde atiende.
- **`apellido` entra en `PROFESSIONAL_FIELDS`.** El fork lo omite, pero la
  validación de receta lo exige y solo se deduce del nombre como fallback: con
  un nombre de una sola palabra la receta queda bloqueada sin arreglo posible
  desde la app.
- **`sexo` acepta los cuatro valores del ENUM.** El fork valida F/M/X y
  convertía `'O'` a NULL en silencio.
- **Los mails de turnos con invitación `.ics`.** Se extrajeron a
  `utils/mails_turnos.py` justo para que sobrevivieran a tomar la versión del
  fork de `turnos_routes.py`.
- **`'Área'` con acento** en `CrearUsuario.vue`; el fork usa `'Area'`.
