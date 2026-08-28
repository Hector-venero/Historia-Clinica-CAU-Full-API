"""Ciclo de vida de la suscripcion de un consultorio.

    prueba  --vence-->  suspendido  --se cancela-->  cancelado  --plazo-->  borrado
       |                     |
       +--paga--> activo <---+ reactivar

La regla que ordena todo lo demas: **suspender no es borrar, y tampoco es
secuestrar**. Un consultorio que dejo de pagar pierde el uso del sistema, pero
sus historias clinicas siguen siendo de sus pacientes y tiene que poder
llevarselas. Por eso `RUTAS_CON_CUENTA_SUSPENDIDA` en tenancy deja vivas la
entrada, el estado y la exportacion.
"""

import os
from datetime import date, datetime

from app import plataforma

# Cuantos dias antes del vencimiento se avisa.
DIAS_PARA_AVISAR = int(os.getenv("DIAS_AVISO_VENCIMIENTO") or "5")

# Cuanto se retiene la base de un consultorio cancelado antes de borrarla.
# No es un numero cualquiera: es el plazo durante el cual todavia se puede
# recuperar todo si alguien se arrepiente o reclama.
DIAS_RETENCION = int(os.getenv("DIAS_RETENCION_CANCELADOS") or "90")


def cambiar_estado(slug, estado, motivo=None):
    """Cambia el estado y deja la marca temporal que corresponde."""
    columna_fecha = {
        "suspendido": "suspendido_en",
        "cancelado": "cancelado_en",
    }.get(estado)

    with plataforma.cursor_plataforma(commit=True) as (_conn, cur):
        if columna_fecha:
            cur.execute(
                f"UPDATE clientes SET estado = %s, motivo_estado = %s, "
                f"{columna_fecha} = NOW() WHERE slug = %s",
                (estado, motivo, slug),
            )
        else:
            # Reactivar limpia las marcas: si no, un consultorio que volvio
            # figuraria como suspendido en cualquier consulta por fecha.
            cur.execute(
                "UPDATE clientes SET estado = %s, motivo_estado = %s, "
                "suspendido_en = NULL, cancelado_en = NULL WHERE slug = %s",
                (estado, motivo, slug),
            )
        cambiados = cur.rowcount

    # El cache de tenancy guarda el cliente hasta 60 segundos. Sin esto, cortar
    # el acceso o devolverlo tardaria hasta un minuto en surtir efecto.
    from app import tenancy

    tenancy.olvidar(slug)
    return cambiados


def registrar_acceso(slug):
    """Marca que alguien entro. Distingue un consultorio que trabaja de uno que
    se dio de alta y no volvio: son conversaciones comerciales distintas."""
    try:
        with plataforma.cursor_plataforma(commit=True) as (_conn, cur):
            cur.execute("UPDATE clientes SET ultimo_acceso = NOW() WHERE slug = %s", (slug,))
    except Exception:
        # Es telemetria: que falle no puede impedir que alguien entre a trabajar.
        pass


def dias_restantes(cliente):
    """Dias que le quedan de prueba. None si no esta en prueba."""
    if cliente.estado != "prueba" or not cliente.prueba_hasta:
        return None
    hasta = cliente.prueba_hasta
    if isinstance(hasta, datetime):
        hasta = hasta.date()
    return (hasta - date.today()).days


def estado_para_mostrar(cliente):
    """Lo que necesita la pantalla para explicarle al usuario que esta pasando."""
    return {
        "estado": cliente.estado,
        "plan": cliente.plan,
        "dias_restantes": dias_restantes(cliente),
        "activo": cliente.activo,
    }


# ------------------------------------------------------- tarea programada


def _pendientes_de_aviso():
    """Pruebas que vencen pronto y a las que todavia no se les aviso."""
    with plataforma.cursor_plataforma() as (_conn, cur):
        cur.execute(
            """
            SELECT * FROM clientes
            WHERE estado = 'prueba'
              AND prueba_hasta IS NOT NULL
              AND aviso_vencimiento_en IS NULL
              AND prueba_hasta <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
              AND prueba_hasta >= CURDATE()
            """,
            (DIAS_PARA_AVISAR,),
        )
        return cur.fetchall()


def _vencidos():
    """Pruebas cuya fecha ya paso y siguen sin pagar."""
    with plataforma.cursor_plataforma() as (_conn, cur):
        cur.execute(
            "SELECT * FROM clientes "
            "WHERE estado = 'prueba' AND prueba_hasta IS NOT NULL AND prueba_hasta < CURDATE()"
        )
        return cur.fetchall()


def revisar(dry_run=False):
    """Avisa a los que estan por vencer y suspende a los vencidos.

    Lo dispara un cron diario. Devuelve el resumen para que el comando lo informe
    y el cron detecte problemas.
    """
    from app.utils.correo import enviar_en_segundo_plano
    from app.utils.mails_suscripcion import mail_aviso_vencimiento, mail_suspendido

    resumen = {"avisados": 0, "suspendidos": 0, "errores": 0}

    for fila in _pendientes_de_aviso():
        try:
            if not dry_run:
                mensaje = mail_aviso_vencimiento(
                    destinatario=fila["email_contacto"],
                    nombre=fila["nombre"],
                    prueba_hasta=fila["prueba_hasta"],
                )
                if mensaje is not None:
                    enviar_en_segundo_plano(mensaje)
                with plataforma.cursor_plataforma(commit=True) as (_c, cur):
                    cur.execute(
                        "UPDATE clientes SET aviso_vencimiento_en = NOW() WHERE id = %s",
                        (fila["id"],),
                    )
            resumen["avisados"] += 1
        except Exception:
            resumen["errores"] += 1

    for fila in _vencidos():
        try:
            if not dry_run:
                cambiar_estado(fila["slug"], "suspendido", "Prueba vencida sin pago")
                mensaje = mail_suspendido(
                    destinatario=fila["email_contacto"], nombre=fila["nombre"]
                )
                if mensaje is not None:
                    enviar_en_segundo_plano(mensaje)
            resumen["suspendidos"] += 1
        except Exception:
            resumen["errores"] += 1

    return resumen


def cancelados_para_borrar():
    """Cancelados cuyo plazo de retencion ya vencio.

    NO borra nada: devuelve la lista. Eliminar la base de un consultorio con
    historias clinicas es irreversible y no puede ser el efecto secundario de un
    cron; que lo decida una persona mirando la lista.
    """
    with plataforma.cursor_plataforma() as (_conn, cur):
        cur.execute(
            "SELECT * FROM clientes "
            "WHERE estado = 'cancelado' AND cancelado_en IS NOT NULL "
            "AND cancelado_en < DATE_SUB(NOW(), INTERVAL %s DAY) "
            "ORDER BY cancelado_en",
            (DIAS_RETENCION,),
        )
        return cur.fetchall()
