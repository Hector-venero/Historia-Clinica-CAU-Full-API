"""Marca, modulos y credenciales: lo que cambia de un consultorio a otro.

Todo lo que aca se resuelve estaba escrito como constante en el codigo o leido
del entorno del proceso, que es lo mismo que decir "igual para todos". Con varios
consultorios en la misma aplicacion eso ya no sirve: cada uno tiene su nombre en
las recetas, su logo en la pantalla de entrada, su token del proveedor y su plan.

**Siempre hay respaldo al entorno.** Sin un consultorio resuelto —el sitio
publico, un comando de consola, el hilo que manda un correo— se devuelven los
valores de las variables de entorno.

Los valores por defecto son los del producto, **Ficha Salud**, y no los de ningun
consultorio: sin inquilino, quien pregunta es la plataforma. Una instalacion de un
solo centro (como la del CAU, que corre en `main`) define MARCA_NOMBRE y
MARCA_NOMBRE_CORTO en su entorno.

Con un consultorio resuelto el default no se usa nunca: gana `nombre_visible` de
su configuracion y, si no lo cargo, el nombre con el que se dio de alta.
"""

import os

from app.utils.secretos import descifrar

# El nombre del producto. Es lo que ve alguien que entra al sitio publico, antes
# de pertenecer a ningun consultorio.
NOMBRE_PRODUCTO = "Ficha Salud"

# Modulos que un plan puede habilitar. El nombre es el que viaja al frontend.
MODULOS_CONOCIDOS = (
    "turnos",
    "pacientes",
    "historias",
    "recetas",
    "grupos",
    "comunicados",
    "blockchain",
)

# Lo que recibe un consultorio si su fila de configuracion todavia no existe.
MODULOS_POR_DEFECTO = ("turnos", "pacientes", "historias", "recetas")


def _cliente():
    """El consultorio del pedido en curso, o None. Import local para no crear
    un ciclo: tenancy importa plataforma, que no tiene por que importar esto."""
    try:
        from app.tenancy import cliente_actual

        return cliente_actual()
    except Exception:
        return None


def _config():
    cliente = _cliente()
    if cliente is None:
        return None
    return cliente.config


def _valor(campo, variable_entorno, por_defecto=None):
    """El campo del consultorio si esta cargado; si no, el entorno."""
    config = _config()
    if config:
        valor = config.get(campo)
        if valor not in (None, ""):
            return valor
    return os.getenv(variable_entorno) or por_defecto


# --------------------------------------------------------------------- marca


def nombre():
    """Nombre completo, el que va en el encabezado de los PDF."""
    cliente = _cliente()
    if cliente is not None:
        config = cliente.config
        if config and config.get("nombre_visible"):
            return config["nombre_visible"]
        return cliente.nombre
    return os.getenv("MARCA_NOMBRE") or NOMBRE_PRODUCTO


def nombre_corto():
    """Version breve, para el pie de pagina y el asunto de los correos."""
    config = _config()
    if config and config.get("nombre_visible"):
        return config["nombre_visible"]
    cliente = _cliente()
    if cliente is not None:
        return cliente.nombre
    return os.getenv("MARCA_NOMBRE_CORTO") or NOMBRE_PRODUCTO


def logo():
    """Ruta del logo del consultorio, o None para usar el del sistema."""
    return _valor("logo", "MARCA_LOGO")


# Logo de la instalacion de un solo centro: el CAU.
#
# Se usa SOLO cuando no hay consultorio resuelto, o sea en `main`, donde ese
# escudo es el correcto. En la plataforma no se usa nunca: ver logo_archivo().
LOGO_INSTALACION = "logo_cau_unsam2.png"


def logo_archivo():
    """El logo como ruta de archivo, para lo que se dibuja en el servidor (PDF).

    `logo()` devuelve lo que va en un `<img src>` del navegador; un PDF necesita
    un archivo en disco, asi que hay que resolverlo.

    ⚠️ **Un consultorio sin logo propio no recibe ninguno.** Devuelve None y
    quien llama pone el nombre en texto. Antes los dos generadores de PDF tenian
    escrita a mano la ruta del escudo de la UNSAM, asi que cualquier consultorio
    emitia historias clinicas con la identidad de otra institucion. Eso no es un
    detalle estetico: es un documento clinico firmado con un logo ajeno.

    El escudo del CAU sigue apareciendo **solo en la instalacion de un solo
    centro**, donde es el que corresponde.
    """
    from flask import current_app

    propio = logo()
    if propio:
        # Puede venir como URL (/static/…) o como nombre de archivo suelto: al
        # PDF solo le sirve el nombre, resuelto dentro de static.
        nombre_archivo = os.path.basename(str(propio).split("?")[0])
        ruta = os.path.join(current_app.root_path, "static", "marcas", nombre_archivo)
        if os.path.exists(ruta):
            return ruta
        # Un logo configurado que no esta en disco no puede caer al de otro:
        # mejor el nombre en texto.
        return None

    if _cliente() is not None:
        return None

    ruta = os.path.join(current_app.root_path, "static", "img", LOGO_INSTALACION)
    return ruta if os.path.exists(ruta) else None


def lugar_atencion():
    """Donde atiende el consultorio. Va en los mails de turnos y en las recetas.

    Es el dato de la institucion, distinto del `lugar_atencion_*` de cada
    profesional, que es donde atiende esa persona.
    """
    return {
        "nombre": _valor("lugar_nombre", "MARCA_LUGAR_NOMBRE"),
        # Sin valor por defecto: un consultorio que no cargo su direccion no
        # puede mostrar la de otro. Antes caia al campus de la UNSAM.
        "direccion": _valor("lugar_direccion", "MARCA_LUGAR_DIRECCION"),
        "telefono": _valor("lugar_telefono", "MARCA_LUGAR_TELEFONO"),
        "email": _valor("lugar_email", "MARCA_LUGAR_EMAIL"),
    }


def publica():
    """Lo minimo para pintar la pantalla de entrada antes de autenticarse.

    Solo nombre y logo: nada que permita averiguar que consultorios existen ni
    conocer su configuracion.
    """
    return {"nombre": nombre(), "nombre_corto": nombre_corto(), "logo": logo()}


# ------------------------------------------------------------------- modulos


def modulos():
    """Modulos habilitados para este consultorio, como conjunto."""
    config = _config()
    if config and config.get("modulos"):
        return {m.strip() for m in config["modulos"].split(",") if m.strip()}

    cliente = _cliente()
    if cliente is not None:
        return set(MODULOS_POR_DEFECTO)

    # Instalacion de un solo centro: todo habilitado, como siempre.
    return set(MODULOS_CONOCIDOS)


def tiene_modulo(nombre_modulo):
    return nombre_modulo in modulos()


def blockchain_habilitado():
    """El anclaje en BFA es opcional y viene apagado.

    Es el diferencial del plan alto, y un consultorio que no lo entiende no tiene
    por que ver la pantalla.
    """
    config = _config()
    if config is not None:
        return bool(config.get("blockchain"))
    if _cliente() is not None:
        return False
    return True


# --------------------------------------------------------------------- recetas


def qbi():
    """Credenciales del proveedor de recetas, por consultorio.

    Cada consultorio factura con su propia cuenta: el token no puede ser del
    sistema. Sin configurar, el modulo responde 503, igual que hoy cuando falta
    QBI_BASE_URL.
    """
    config = _config()
    if config and config.get("qbi_base_url"):
        token = config.get("qbi_token")
        return {
            "base_url": (config.get("qbi_base_url") or "").rstrip("/"),
            "client_id": config.get("qbi_client_id"),
            "token": descifrar(token) if token else None,
        }

    if _cliente() is not None:
        # Consultorio sin recetas configuradas. No se cae al token del entorno:
        # emitiria contra la cuenta de otro.
        return {"base_url": "", "client_id": None, "token": None}

    # Instalacion de un solo centro: sale de la configuracion de Flask, que es
    # donde config.py deja las variables de entorno. Leer os.getenv aca saltearia
    # cualquier valor puesto sobre app.config.
    try:
        from flask import current_app

        cfg = current_app.config
        return {
            "base_url": (cfg.get("QBI_BASE_URL") or "").rstrip("/"),
            "client_id": cfg.get("QBI_CLIENT_ID"),
            "token": cfg.get("QBI_TOKEN"),
        }
    except Exception:
        return {
            "base_url": (os.getenv("QBI_BASE_URL") or "").rstrip("/"),
            "client_id": os.getenv("QBI_CLIENT_ID"),
            "token": os.getenv("QBI_TOKEN"),
        }
