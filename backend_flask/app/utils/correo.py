"""Envio de correo en segundo plano.

El envio era sincrono dentro del request: si el servidor SMTP estaba lento, la
respuesta de la API se demoraba lo mismo. Se detecto porque la suite de tests
tardaba 8 segundos, esperando el timeout del correo en cada emision de receta.

Un turno agendado o una receta emitida ya son hechos consumados cuando toca
mandar el aviso: no tiene sentido que el usuario espere por eso, ni que un SMTP
caido haga fallar la operacion.

No es una cola con reintentos ni persistencia. Es un hilo por mensaje, que para
el volumen de este sistema (unos pocos correos por consulta) alcanza. Si algun
dia hace falta garantizar la entrega, el punto de cambio es este modulo.
"""

import threading

from flask import current_app


def enviar_en_segundo_plano(mensaje):
    """Manda el mensaje sin bloquear el request.

    El hilo necesita su propio contexto de aplicacion: fuera del request,
    current_app ya no existe y Flask-Mail no podria leer la configuracion.
    """
    app = current_app._get_current_object()

    def _enviar():
        with app.app_context():
            try:
                app.extensions["mail"].send(mensaje)
            except Exception:
                # Se registra y se descarta: el aviso es accesorio, la operacion
                # que lo origino ya termino bien.
                app.logger.exception("No se pudo enviar el correo a %s", mensaje.recipients)

    hilo = threading.Thread(target=_enviar, name="envio-correo", daemon=True)
    hilo.start()
    return hilo
