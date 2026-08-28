"""Resuelve a que consultorio pertenece cada pedido, a partir del subdominio.

    drlopez.miproducto.com  ->  cliente 'drlopez'  ->  base hc_drlopez

Es la pieza que convierte una aplicacion de un solo centro medico en una que
atiende a muchos, y es deliberadamente chica: lo unico que hace es dejar el
cliente en `flask.g`. Quien decide que base usar es `database.get_connection()`,
que ya era el unico lugar del sistema que lo decidia. Las 184 consultas siguen
sin enterarse de que existen otros consultorios.

**El modo multi-inquilino esta apagado por defecto.** Sin MULTI_TENANT=true, todo
se comporta como siempre y la base sale de las variables de entorno: es lo que
mantiene funcionando la instalacion del CAU con este mismo codigo.
"""

import os
import time

from flask import g, jsonify, request, session
from flask_login import user_logged_in

from app import plataforma

# Clave con la que la sesion recuerda de que consultorio es.
#
# La cookie de sesion va firmada con SECRET_KEY, que es de la plataforma y por lo
# tanto la misma para todos los clientes, y adentro solo lleva el id del usuario.
# Como cada base tiene su propio usuario 1, una sesion de un consultorio
# **autentica en otro**: comprobado reenviando la cookie a mano, respondia 200
# como el admin del otro consultorio.
#
# En un navegador la cookie queda acotada al host y no viaja sola, pero eso es
# una defensa del navegador, no del sistema: una cookie robada servia en todos
# los consultorios, y bastaba con que alguien definiera SESSION_COOKIE_DOMAIN
# para romper el aislamiento entero.
CLAVE_SESION = "_cliente"

# Cache en memoria del catalogo de clientes. Sin esto, cada pedido consulta el
# plano de control antes de hacer nada: es la consulta mas repetida de todo el
# sistema y su respuesta casi nunca cambia.
#
# El TTL es corto a proposito: suspender a un cliente por falta de pago tiene que
# surtir efecto en minutos, no cuando se reinicie el proceso.
TTL_CACHE_SEGUNDOS = int(os.getenv("TTL_CACHE_CLIENTES") or "60")

_cache = {}


def multi_tenant_activo():
    return (os.getenv("MULTI_TENANT") or "").strip().lower() == "true"


def dominio_base():
    """El dominio bajo el que cuelgan los subdominios de los clientes.

    De `drlopez.miproducto.com` con DOMINIO_BASE=miproducto.com sale 'drlopez'.
    """
    return (os.getenv("DOMINIO_BASE") or "").strip().lower().strip(".")


def slug_desde_host(host):
    """Extrae el slug del encabezado Host. Devuelve None si no hay subdominio.

    Tolera el puerto (`drlopez.localhost:5000`), porque en desarrollo el Host
    llega con el puerto incluido y sin esto ningun subdominio resolveria.
    """
    if not host:
        return None

    host = host.split(":")[0].strip().lower().rstrip(".")
    base = dominio_base()

    if base:
        if host == base or not host.endswith("." + base):
            # El dominio raiz es el sitio publico (registro, precios), no un
            # consultorio.
            return None
        etiqueta = host[: -(len(base) + 1)]
    else:
        # Sin DOMINIO_BASE configurado se toma la primera etiqueta. Sirve para
        # desarrollo (drlopez.localhost) pero en produccion conviene declararlo:
        # si no, cualquier host que apunte al servidor resuelve como cliente.
        partes = host.split(".")
        if len(partes) < 2:
            return None
        etiqueta = partes[0]

    # Un subdominio de varios niveles (a.b.miproducto.com) no es un cliente.
    if not etiqueta or "." in etiqueta:
        return None
    if etiqueta in ("www", "api", "app"):
        return None

    return etiqueta


# Lo unico que sigue atendiendo con la cuenta suspendida.
#
# Suspender por falta de pago no puede significar secuestrar historias clinicas:
# son datos del paciente, no del proveedor. Asi que se deja entrar, ver que pasa
# y llevarse todo. Lo que se corta es usar el sistema para trabajar.
#
# Es una lista explicita y no un patron: cada ruta que siga viva estando
# suspendido tiene que ser una decision consciente.
RUTAS_CON_CUENTA_SUSPENDIDA = (
    "/api/login",
    "/api/logout",
    "/api/usuarios/me",
    "/api/publico/marca",
    "/api/cuenta/",
)


def _permitido_estando_suspendido(path):
    return path.startswith(RUTAS_CON_CUENTA_SUSPENDIDA)


def _desde_cache(slug):
    entrada = _cache.get(slug)
    if not entrada:
        return None
    cliente, guardado_en = entrada
    if time.time() - guardado_en > TTL_CACHE_SEGUNDOS:
        _cache.pop(slug, None)
        return None
    return cliente


def resolver(slug):
    """Devuelve el Cliente del slug, con cache. None si no existe."""
    if not slug:
        return None

    cliente = _desde_cache(slug)
    if cliente is not None:
        return cliente

    cliente = plataforma.buscar_por_slug(slug)
    if cliente is not None:
        _cache[slug] = (cliente, time.time())
    return cliente


def olvidar(slug=None):
    """Invalida el cache. Al dar de alta, suspender o reactivar un cliente."""
    if slug:
        _cache.pop(slug, None)
    else:
        _cache.clear()


def cliente_actual():
    """El consultorio del pedido en curso, o None fuera de un request."""
    return getattr(g, "cliente", None)


def registrar(app):
    """Engancha la resolucion al ciclo de pedidos.

    Va antes que cualquier otro before_request: el cargador de usuario de
    Flask-Login consulta la base, y sin el cliente resuelto no sabria a cual.
    """

    @app.before_request
    def _resolver_cliente():
        g.cliente = None

        if not multi_tenant_activo():
            # Instalacion de un solo consultorio: la base sale del entorno.
            return None

        # El chequeo de salud tiene que responder aunque el Host no resuelva:
        # es lo que mira el monitoreo de la plataforma, no de un cliente.
        if request.path.startswith("/api/health/"):
            return None

        # El alta autoservicio atiende en el dominio raiz: quien se registra
        # todavia no tiene subdominio. Es una lista corta y cerrada, y no una
        # regla general, para que agregar rutas publicas sea una decision
        # explicita y no algo que pase sin que nadie lo mire.
        if request.path.startswith("/api/registro"):
            return None

        slug = slug_desde_host(request.headers.get("Host", ""))
        if not slug:
            return jsonify({
                "error": "No se indico ningun consultorio.",
                "detalle": "Se entra por el subdominio del consultorio.",
            }), 404

        cliente = resolver(slug)
        if cliente is None:
            # Mismo mensaje que para un slug con formato invalido: distinguirlos
            # permitiria averiguar que consultorios existen probando nombres.
            return jsonify({"error": "El consultorio no existe."}), 404

        # El cliente queda resuelto aunque este suspendido: sin esto la conexion
        # no sabria a que base ir, y un consultorio suspendido no podria ni
        # siquiera exportar sus datos.
        g.cliente = cliente

        if not cliente.activo:
            # Los datos no se borran ni se vuelven inaccesibles: son del
            # paciente, no del proveedor. Se corta el uso normal del sistema,
            # pero se deja entrar, ver el estado y llevarse la historia clinica.
            if not _permitido_estando_suspendido(request.path):
                return jsonify({
                    "error": "La cuenta esta suspendida.",
                    "estado": cliente.estado,
                    "detalle": "Podes exportar tus datos o reactivar la cuenta.",
                }), 402

        # Una sesion abierta en otro consultorio no vale aca, aunque la cookie
        # este bien firmada y el id de usuario exista en esta base.
        marcado = session.get(CLAVE_SESION)
        if marcado is not None and marcado != cliente.slug:
            session.clear()
            return jsonify({"error": "No autorizado"}), 401

        g.cliente = cliente
        return None

    @user_logged_in.connect_via(app)
    def _marcar_consultorio(_sender, user, **_extra):
        """Deja anotado en la sesion de que consultorio es.

        Va por la senal de Flask-Login y no dentro de la vista de login: asi
        vale para cualquier camino que inicie sesion, presente o futuro, sin
        depender de que alguien se acuerde de agregarlo.
        """
        cliente = getattr(g, "cliente", None)
        if cliente is not None:
            session[CLAVE_SESION] = cliente.slug
