# Videoconsulta

**Estado:** funcionando desde el 30/08/2026, en su versión más chica: el turno
lleva una modalidad y, si es virtual, el enlace de la videollamada.

Lo que sigue explica **por qué se hizo así** y qué haría falta para ir más lejos,
porque la pregunta "¿no convenía Google Meet o Zoom?" se va a repetir.

---

## Lo que hace hoy

- El turno tiene `modalidad` (`presencial` | `virtual`) y `enlace_video`.
- El profesional pega el enlace de la sala que ya usa. **El sistema no genera ni
  aloja la videollamada.**
- El enlace le llega al paciente por tres caminos: el correo de confirmación con
  un botón, el `LOCATION` del `.ics` adjunto —que es de donde lo saca el botón
  "unirse" del calendario del celular— y su portal.
- En el portal, el botón para entrar aparece **30 minutos antes** del turno y
  hasta dos horas después. Un botón visible tres semanas antes invita a entrar a
  una sala vacía y a pensar que el sistema está roto.
- La reserva online entra siempre como presencial. El profesional puede pasarla
  a virtual después: el portal lee la modalidad del consultorio, no de su copia,
  así que el paciente lo ve sin que haya que reenviarle nada.

## Lo que no hace, a propósito

- **No graba.** Grabar una consulta médica abre un problema legal y de
  almacenamiento que hoy no conviene tener. No es una limitación técnica.
- No hay sala de espera, ni control de quién entra, ni cifrado propio: eso lo
  pone la herramienta que elija el profesional.

---

## Por qué un enlace y no video embebido

La decisión no fue "Jitsi contra Google". Fue **"enlace hacia afuera" contra
"video adentro del producto"**, y ahí las opciones no son equivalentes:

| | ¿Se puede embeber? | Qué cuesta |
|---|---|---|
| **Google Meet** | No. No existe API para incrustarlo. | Generar el enlace desde el sistema exige la API de Calendar con OAuth de cada profesional. Termina igual afuera. |
| **Zoom** | Sí, con su SDK. | Credenciales de app, OAuth por profesional y plan pago. En el gratuito, más de dos participantes se corta a los 40 minutos: con un familiar acompañando, pasa. |
| **Jitsi** | Sí, con un iframe. | El servidor público no sirve para producción (sin acuerdo de servicio, y las salas son adivinables si el nombre no es aleatorio). En serio implica la versión administrada de pago o alojarlo uno mismo. |

Y lo que juega en contra de meter video propio ahora: **un médico que hoy hace
teleconsulta ya tiene su herramienta**. Ponerle otra es pedirle que cambie algo
que no le molesta. El campo de enlace no es "la opción barata": es la que respeta
eso, y sirve para las tres.

## Cuándo convendría dar el paso siguiente

Cuando un consultorio real use videoconsulta seguido. Ahí el candidato es
**Jitsi autoalojado**, por dos motivos:

1. Queda **dentro** del producto: el paciente entra desde su portal sin instalar
   nada ni crear cuenta, que es justo el argumento del portal.
2. Con datos de salud y la Ley 25.326 encima, que la videoconsulta de un paciente
   argentino no viaje por la infraestructura de un tercero es un argumento de
   venta, no un detalle técnico.

Lo que habría que resolver entonces —y no está resuelto hoy—: salas con nombre
aleatorio y firmadas para que solo entre quien tiene turno, que se abran cerca
del horario, y el consentimiento de la teleconsulta.

**Nada de eso tira lo que hay.** El campo de enlace sigue existiendo para quien
prefiera su Zoom de siempre.

⚠️ Los precios y límites de estos servicios cambian seguido. Verificar antes de
comprometerse con cualquiera de los tres.

---

## Dónde está en el código

| | |
|---|---|
| Validación | `routes/turnos_routes.py` → `_leer_modalidad()` |
| Escritura | los dos `INSERT INTO turnos` y el `UPDATE` de `editar_turno` |
| Correo y `.ics` | `utils/mails_turnos.py` → `_bloque_lugar()`, `construir_ics()` |
| Lo que ve el paciente | `reservas.mis_turnos()` y `views/pages/portal/MisTurnos.vue` |
| Esquema | `db/migrations/20260901_turnos_modalidad.sql` |
| Tests | `tests/test_turnos_modalidad.py` |

La validación **es del servidor**. El formulario ayuda, pero un enlace que no
empieza con `https://` se rechaza en el backend: termina en un correo a un
paciente, y el error se descubriría a la hora del turno.
