"""Ubicacion en disco de los archivos adjuntos de las evoluciones.

Las rutas estaban armadas a mano en cinco lugares de pacientes_routes.py, todas
con `os.path.join(os.getcwd(), 'uploads', ...)`. Eso traia dos problemas.

**El directorio de trabajo no es el mismo en desarrollo que en produccion.** En
desarrollo `flask run` corre desde /app y os.getcwd() devuelve /app, que coincide
con el volumen. Pero start.sh arranca gunicorn con `--chdir /`, asi que en
produccion os.getcwd() devuelve `/` y los adjuntos terminan en /uploads, fuera
del volumen montado en /app/uploads. Comprobado:

    gunicorn --chdir / ...  ->  CWD AL CARGAR: /

Es decir: en produccion los archivos se escriben en la capa efimera del
contenedor y **se pierden en cada reinicio**, mientras nginx sirve el volumen
—vacio— y la aplicacion los busca en una ruta que solo existe hasta el proximo
despliegue. Ahora la base sale de UPLOAD_FOLDER, que es una ruta absoluta.

**No habia separacion por cliente.** El id de la evolucion es autoincremental por
base de datos, de modo que con una base por consultorio dos clientes tendrian
ambos la evolucion 1 y colisionarian en el mismo volumen. Por eso el cliente es
el primer segmento de la ruta.

No hace falta defenderse del path traversal aca: send_from_directory de Flask 3
usa safe_join internamente.
"""

import os
import pathlib

from flask import current_app, g

# Mientras la plataforma no resuelva inquilinos (F3), todo vive bajo este
# segmento. Al llegar la multi-tenencia, `segmento_cliente()` empieza a devolver
# el slug real y las rutas quedan separadas sin tocar a quien las usa.
CLIENTE_POR_DEFECTO = "principal"


def segmento_cliente():
    """Carpeta raiz del cliente actual.

    Sale de `flask.g` cuando hay un inquilino resuelto. Fuera del ciclo de
    request —migraciones, tareas de consola, hilos de correo— no hay `g`, asi
    que se cae al valor por defecto en lugar de reventar.
    """
    cliente = getattr(g, "cliente", None) if g else None
    slug = getattr(cliente, "slug", None) if cliente else None
    return slug or CLIENTE_POR_DEFECTO


def carpeta_base():
    """Raiz de los adjuntos, absoluta. Coincide con el volumen uploads_data."""
    return pathlib.Path(current_app.config["UPLOAD_FOLDER"])


def carpeta_evolucion(evolucion_id, crear=False):
    """Directorio de los adjuntos de una evolucion."""
    carpeta = carpeta_base() / segmento_cliente() / "evoluciones" / str(evolucion_id)
    if crear:
        os.makedirs(carpeta, exist_ok=True)
    return carpeta


def ruta_adjunto(evolucion_id, nombre_archivo):
    """Ruta completa de un adjunto concreto."""
    return carpeta_evolucion(evolucion_id) / nombre_archivo


def url_adjunto(evolucion_id, nombre_archivo, base=""):
    """URL por la que se sirve el adjunto.

    Siempre por /api/, que exige sesion. nginx ya no publica el volumen: lo
    servia en /uploads/ sin autenticacion, de modo que cualquiera con la URL
    descargaba un archivo clinico sin estar logueado.
    """
    return f"{base}/api/uploads/evoluciones/{evolucion_id}/{nombre_archivo}"
