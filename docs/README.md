# Documentación

| Documento | Qué contiene |
|---|---|
| [PENDIENTES.md](PENDIENTES.md) | **Lo que está abierto.** Empezar por acá |
| [SAAS.md](SAAS.md) | **La plataforma multi-consultorio.** Por qué una base por cliente, cómo se resuelve el inquilino, el alta autoservicio, el ciclo de la suscripción y las reglas que no se negocian |
| [../deploy/PLATAFORMA.md](../deploy/PLATAFORMA.md) | Poner la plataforma en un VPS: DNS comodín, certificado, cron y copias por consultorio |
| [VIDEOCONSULTA.md](VIDEOCONSULTA.md) | **Por qué la videoconsulta es un enlace y no video embebido**, qué haría falta para Jitsi autoalojado y por qué no se graba |
| [RECONCILIACION-FORK.md](RECONCILIACION-FORK.md) | Qué se trajo del fork de GeroGauna222, qué no, y qué se cambió al traerlo |
| [MEJORAS-QA.md](MEJORAS-QA.md) | Registro cerrado de los 15 problemas de la pasada de QA del 25/08/2026 |

Los chequeos mecánicos del frontend —enlaces a rutas inexistentes y colores sin
variante oscura— viven en [`../scripts/revisiones/`](../scripts/revisiones/),
con su propio README.

La guía operativa —cómo levantar el entorno, la arquitectura, las reglas del
esquema y las convenciones— está en [`CLAUDE.md`](../CLAUDE.md) en la raíz. Es
el documento que hay que mantener al día: se carga en cada sesión de trabajo
con Claude Code y es lo primero que se lee.

El [`README.md`](../README.md) de la raíz es la presentación del proyecto, para
quien lo abre por primera vez.
