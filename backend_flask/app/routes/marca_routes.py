"""La marca del consultorio: subir su logo.

La columna `clientes_config.logo` y `marca.logo()` existian desde el principio,
y la barra superior ya la usaba. Lo que faltaba era la forma de cargarlo: hasta
ahora solo se podia escribiendo la base a mano.

Importa mas de lo que parece. Sin logo propio, el PDF de una historia clinica
sale con el nombre del consultorio en texto — que esta bien, pero es lo minimo—,
y antes salia directamente con el escudo de la UNSAM.
"""

import os

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_login import login_required
from werkzeug.utils import secure_filename

from app import marca, plataforma
from app.tenancy import cliente_actual, olvidar
from app.utils.permisos import requiere_rol

bp_marca = Blueprint("marca", __name__)

# Formatos que un navegador dibuja y que reportlab sabe poner en un PDF.
#
# SVG queda afuera a proposito: reportlab no lo dibuja sin dependencias extra, y
# un logo que se ve en la pantalla pero no en el PDF es peor que no tenerlo.
EXTENSIONES = {"png", "jpg", "jpeg", "webp"}

# 2 MB. Un logo es un logo: mas que eso es una foto subida por error.
TAMANO_MAXIMO = 2 * 1024 * 1024

CARPETA = "marcas"


def _carpeta():
    """Se resuelve desde root_path y no con una ruta absoluta: `/app/static/...`
    solo existe dentro del contenedor, y correr el backend afuera rompia la
    subida de fotos por exactamente eso."""
    ruta = os.path.join(current_app.root_path, "static", CARPETA)
    os.makedirs(ruta, exist_ok=True)
    return ruta


@bp_marca.get("/api/marca")
@login_required
def obtener():
    """Lo que hay cargado hoy. El nombre sale de la marca resuelta."""
    return jsonify(
        {
            "nombre": marca.nombre(),
            "nombre_corto": marca.nombre_corto(),
            "logo": marca.logo(),
        }
    )


@bp_marca.post("/api/marca/logo")
@login_required
@requiere_rol("director")
def subir_logo():
    """Sube el logo del consultorio. Solo la direccion del consultorio."""
    cliente = cliente_actual()
    if cliente is None:
        # En la instalacion de un solo centro el logo viene del entorno
        # (MARCA_LOGO): no hay plano de control donde guardarlo.
        return jsonify({"error": "Esta instalacion no tiene marca por consultorio."}), 400

    archivo = request.files.get("logo")
    if archivo is None or not archivo.filename:
        return jsonify({"error": "No llego ningun archivo."}), 400

    extension = archivo.filename.rsplit(".", 1)[-1].lower() if "." in archivo.filename else ""
    if extension not in EXTENSIONES:
        return jsonify({
            "error": "Formato no admitido. Usa PNG, JPG o WEBP.",
        }), 400

    # El tamano se mide sobre el stream y no con Content-Length, que lo manda
    # quien sube y por lo tanto no es un dato confiable.
    archivo.seek(0, os.SEEK_END)
    tamano = archivo.tell()
    archivo.seek(0)
    if tamano > TAMANO_MAXIMO:
        return jsonify({"error": "El archivo supera los 2 MB."}), 400

    # El nombre lleva el slug del consultorio: los logos de todos los clientes
    # comparten carpeta, y un nombre tomado del archivo subido dejaria que uno
    # pisara el de otro.
    nombre_archivo = secure_filename(f"{cliente.slug}.{extension}")
    destino = os.path.join(_carpeta(), nombre_archivo)

    # Un cambio de formato deja el anterior colgado: se limpian los otros.
    for otra in EXTENSIONES:
        viejo = os.path.join(_carpeta(), secure_filename(f"{cliente.slug}.{otra}"))
        if otra != extension and os.path.exists(viejo):
            os.remove(viejo)

    archivo.save(destino)

    url = f"/static/{CARPETA}/{nombre_archivo}"
    plataforma.guardar_config(cliente.id, logo=url)

    # El catalogo esta cacheado en memoria: sin invalidar, el logo nuevo tarda
    # hasta el TTL en verse, y quien lo acaba de subir cree que no se guardo.
    olvidar(cliente.slug)

    return jsonify({"logo": url, "message": "Logo actualizado"}), 200


@bp_marca.delete("/api/marca/logo")
@login_required
@requiere_rol("director")
def borrar_logo():
    cliente = cliente_actual()
    if cliente is None:
        return jsonify({"error": "Esta instalacion no tiene marca por consultorio."}), 400

    for extension in EXTENSIONES:
        ruta = os.path.join(_carpeta(), secure_filename(f"{cliente.slug}.{extension}"))
        if os.path.exists(ruta):
            os.remove(ruta)

    plataforma.guardar_config(cliente.id, logo=None)
    olvidar(cliente.slug)

    return jsonify({"message": "Logo eliminado"}), 200


@bp_marca.get("/api/ajustes")
@login_required
@requiere_rol("director", "administrativo")
def leer_ajustes():
    """Los avisos del consultorio, con su titulo y su explicacion.

    El texto viaja desde el servidor (`ajustes.descripcion()`) para que sumar un
    aviso sea un solo lugar: la pantalla se dibuja con lo que reciba.
    """
    from app import ajustes

    return jsonify({"ajustes": ajustes.descripcion()})


@bp_marca.put("/api/ajustes")
@login_required
@requiere_rol("director")
def guardar_ajustes():
    """Apagar los avisos del consultorio es de la direccion.

    Un administrativo puede verlos —para saber por que un paciente no recibio
    el correo— pero no decidir que el consultorio deje de avisar.
    """
    from app import ajustes

    datos = request.get_json(silent=True) or {}
    ajustes.guardar(datos.get("ajustes") or datos)
    return jsonify({"ajustes": ajustes.descripcion(), "message": "Ajustes guardados"})


@bp_marca.get("/static/marcas/<path:nombre>")
@bp_marca.get("/api/static/marcas/<path:nombre>")
def servir_logo(nombre):
    """El logo se ve sin sesion: esta en la pantalla de entrada del consultorio.

    No es informacion clinica — es la identidad publica del consultorio, la misma
    que aparece en el directorio.
    """
    return send_from_directory(_carpeta(), nombre)
