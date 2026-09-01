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

# Que incluye cada plan.
#
# Hasta ahora `clientes.plan` era un texto que **no se traducia a modulos en
# ninguna parte**: los modulos vivian sueltos en `clientes_config.modulos` y la
# unica forma de cambiarlos era escribir la base a mano. Vender un plan y no
# tener donde este escrito que incluye es como no tener planes.
#
# Las claves son las mismas que las de la pagina de precios
# (`publico/datos.js` → PLANES). Que el sistema y el sitio usen dos vocabularios
# distintos es como empieza a venderse una cosa y entregarse otra.
#
# `basico` es el nombre que puso el script de alta antes de que esto existiera.
# Se conserva como sinonimo de `profesional` en vez de renombrarlo en la base:
# renombrar es una migracion sobre clientes vivos para arreglar un alias.
PLANES = {
    "profesional": {
        "modulos": ("turnos", "pacientes", "historias", "recetas"),
        "blockchain": False,
    },
    "equipo": {
        "modulos": (
            "turnos", "pacientes", "historias", "recetas",
            "grupos", "comunicados", "blockchain",
        ),
        "blockchain": True,
    },
}
PLANES["basico"] = PLANES["profesional"]

# Nombre para mostrar. El plan se le muestra a quien lo paga, y "basico" no es
# como se llama en ningun lado de cara al cliente.
NOMBRE_DE_PLAN = {
    "profesional": "Profesional",
    "basico": "Profesional",
    "equipo": "Equipo",
}

# Con que se queda un consultorio cuyo plan no figura en el mapa. El plan chico
# y no el grande: equivocarse para arriba es regalar lo que se vende, y nadie
# reclama por eso — asi que no se entera nadie.
PLAN_POR_DEFECTO = "profesional"

# Lo que recibe un consultorio si su fila de configuracion todavia no existe.
MODULOS_POR_DEFECTO = PLANES[PLAN_POR_DEFECTO]["modulos"]


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


def _definicion_del_plan(cliente):
    """Lo que incluye el plan del consultorio, con respaldo al plan chico."""
    clave = (getattr(cliente, "plan", None) or "").strip().lower()
    return PLANES.get(clave) or PLANES[PLAN_POR_DEFECTO]


def plan():
    """El plan del consultorio: clave y nombre para mostrar.

    None en la instalacion de un solo centro, que no tiene plan que mostrar.
    """
    cliente = _cliente()
    if cliente is None:
        return None
    clave = (getattr(cliente, "plan", None) or PLAN_POR_DEFECTO).strip().lower()
    return {
        "clave": clave,
        "nombre": NOMBRE_DE_PLAN.get(clave, clave.capitalize()),
    }


def modulos():
    """Modulos habilitados para este consultorio, como conjunto.

    El orden importa:

    1. `clientes_config.modulos`, si esta cargado. Es un **override**, y existe
       para poder venderle un modulo suelto a un consultorio sin inventar un
       plan nuevo por cada combinacion.
    2. Lo que incluye su plan.
    3. Todo, en la instalacion de un solo centro, que no tiene planes.

    Antes el paso 2 no existia: sin fila de configuracion todos recibian la
    misma lista fija, con lo que el plan no encendia nada y contratar el grande
    no cambiaba ni una pantalla.
    """
    config = _config()
    if config and config.get("modulos"):
        return {m.strip() for m in config["modulos"].split(",") if m.strip()}

    cliente = _cliente()
    if cliente is not None:
        return set(_definicion_del_plan(cliente)["modulos"])

    # Instalacion de un solo centro: todo habilitado, como siempre.
    return set(MODULOS_CONOCIDOS)


def tiene_modulo(nombre_modulo):
    return nombre_modulo in modulos()


def modulos_no_incluidos():
    """Los que existen y este consultorio no tiene.

    El frontend los usa para **mostrarlos igual, con candado**, en vez de
    esconderlos. Un consultorio que nunca ve que existen los comunicados o las
    agendas de grupo no los va a contratar nunca: esconder lo que no se contrato
    protege al que no paga de una frustracion y le cuesta la venta al que si
    pagaria.
    """
    return sorted(set(MODULOS_CONOCIDOS) - modulos())


def blockchain_habilitado():
    """El anclaje en BFA es opcional y viene apagado.

    Es el diferencial del plan alto, y un consultorio que no lo entiende no tiene
    por que ver la pantalla.
    """
    config = _config()
    if config is not None:
        return bool(config.get("blockchain"))
    cliente = _cliente()
    if cliente is not None:
        # Sin fila de configuracion manda el plan, igual que los modulos.
        return bool(_definicion_del_plan(cliente)["blockchain"])
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
