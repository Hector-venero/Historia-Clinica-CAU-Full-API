# Documentación

## Lo que hay que leer primero

| Documento | Qué contiene |
|---|---|
| [QA-2026-09.md](QA-2026-09.md) | **La lista viva.** Los trece hallazgos de la pasada de septiembre, con lo que se ve, lo que se verificó en el código y dónde |
| [PENDIENTES.md](PENDIENTES.md) | Lo abierto que **no** entra en esa pasada: rotar los secretos, dominio, lo que no se pudo verificar de la plataforma |

⚠️ **Una cosa abierta vive en una sola de las dos.** Cuando lo mismo figuraba en
las dos listas, la que no se tocaba quedaba vieja sin que nadie se enterara. Al
cerrarse la pasada de QA, lo que quede sin resolver vuelve a `PENDIENTES.md`.

## La guía permanente

| Documento | Qué contiene |
|---|---|
| [`../CLAUDE.md`](../CLAUDE.md) | **El que hay que mantener al día.** Cómo levantar el entorno, la arquitectura, las reglas del esquema y las convenciones. Se carga en cada sesión de trabajo y es lo primero que se lee |
| [SAAS.md](SAAS.md) | La plataforma multi-consultorio: por qué una base por cliente, cómo se resuelve el inquilino, el alta autoservicio, el ciclo de la suscripción y lo que se aprendió usándola |
| [VIDEOCONSULTA.md](VIDEOCONSULTA.md) | Por qué la videoconsulta es un enlace y no video embebido, qué haría falta para Jitsi autoalojado y por qué no se graba |
| [RECONCILIACION-FORK.md](RECONCILIACION-FORK.md) | Qué se trajo del fork de GeroGauna222, qué **no**, y por qué. Evita volver a discutir lo ya decidido |
| [`../deploy/PLATAFORMA.md`](../deploy/PLATAFORMA.md) | Poner la plataforma en un VPS: DNS comodín, certificado, cron y copias por consultorio |
| [`../scripts/revisiones/`](../scripts/revisiones/) | Los dos chequeos mecánicos del frontend: enlaces a rutas inexistentes y colores sin variante oscura |

El [`README.md`](../README.md) de la raíz es la presentación del proyecto, para
quien lo abre por primera vez.

## Lo cerrado

[`historico/`](historico/) guarda los registros terminados. No se consultan a
diario, pero **no se borran**: lo que vale de ellos es *por qué* se resolvió
algo, y varias veces la conclusión terminó siendo distinta del reporte original.

## Cuándo se borra un ítem cerrado

Un ítem tachado se puede eliminar **cuando su lección ya está escrita en
`CLAUDE.md` o en `SAAS.md`**, no cuando "pasa un tiempo". Mientras la enseñanza
viva solo en la lista de pendientes, borrarla la pierde.

Ejemplo de cómo se aplica: el ítem de la zona horaria se eliminó de
`PENDIENTES.md` recién **después** de subir a `CLAUDE.md` la regla que lo evita
—que toda fecha en un JSON pase por `a_iso_arg()`, porque `jsonify` las etiqueta
como GMT—. Primero se absorbe la lección; después se borra el ítem.
