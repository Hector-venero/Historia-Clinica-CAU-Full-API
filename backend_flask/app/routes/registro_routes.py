"""Alta autoservicio. Vive en el dominio raiz, no en el de un consultorio.

Son las unicas rutas que atienden sin consultorio resuelto: quien se registra
todavia no tiene subdominio. Por eso `tenancy` las exime explicitamente, con una
lista corta y cerrada en lugar de una regla general.
"""

from flask import Blueprint, current_app, jsonify, request

from app import registro
from app.utils.correo import enviar_en_segundo_plano
from app.utils.mails_registro import mail_bienvenida, mail_verificacion

bp_registro = Blueprint("registro", __name__, url_prefix="/api/registro")


def _url_consultorio(slug):
    """La direccion final del consultorio, para el correo y la redireccion."""
    dominio = (current_app.config.get("DOMINIO_BASE") or "").strip().strip(".")
    if not dominio:
        # En desarrollo se trabaja con `slug.localhost:5173`.
        return f"http://{slug}.localhost:5173"
    esquema = "https" if current_app.config.get("ENV") == "production" else "http"
    return f"{esquema}://{slug}.{dominio}"


@bp_registro.get("/disponible")
def slug_disponible():
    """Consulta en vivo mientras se escribe la direccion deseada.

    Devuelve el motivo para poder mostrarlo debajo del campo, sin distinguir
    'ocupado' de 'reservado': esa diferencia solo serviria para averiguar que
    consultorios existen.
    """
    try:
        # Devuelve el slug ya normalizado. Escribir "Consultorio-Lopez" da una
        # direccion valida, pero en minusculas: si la respuesta fuera solo
        # "disponible", el formulario mostraria una direccion distinta de la que
        # va a quedar.
        normalizado = registro.validar_slug(request.args.get("slug"))
    except registro.ErrorRegistro as exc:
        return jsonify({"disponible": False, "motivo": str(exc)})
    return jsonify({"disponible": True, "slug": normalizado})


@bp_registro.post("")
@bp_registro.post("/")
def crear_registro():
    """Guarda la intencion de alta y manda el correo de verificacion.

    No crea ninguna base: el formulario es publico y crear una base por cada
    envio permitiria llenar el servidor con un script.
    """
    datos = request.get_json(silent=True) or {}

    try:
        token = registro.registrar(datos)
    except registro.ErrorRegistro as exc:
        return jsonify({"error": str(exc)}), 400

    mensaje = mail_verificacion(
        destinatario=(datos.get("email") or "").strip().lower(),
        nombre=(datos.get("nombre") or "").strip(),
        token=token,
    )
    if mensaje is not None:
        enviar_en_segundo_plano(mensaje)

    # El token no viaja en la respuesta: el unico camino para seguir es el
    # correo, que es justamente lo que se esta verificando.
    return jsonify({
        "mensaje": "Te mandamos un correo para confirmar tu direccion.",
    }), 202


@bp_registro.post("/verificar/<token>")
def verificar(token):
    """Confirma el correo y crea el consultorio."""
    try:
        fila = registro.verificar_y_crear(token)
    except registro.ErrorRegistro as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Fallo la creacion del consultorio")
        return jsonify({
            "error": "No pudimos crear tu consultorio. Escribinos y lo resolvemos.",
        }), 500

    url = _url_consultorio(fila["slug"])

    if fila["estado"] == "listo" and not fila.get("_avisado"):
        mensaje = mail_bienvenida(
            destinatario=fila["email"], nombre=fila["nombre"], url=url
        )
        if mensaje is not None:
            enviar_en_segundo_plano(mensaje)

    return jsonify({
        "estado": fila["estado"],
        "slug": fila["slug"],
        "url": url,
    })


@bp_registro.get("/estado/<token>")
def estado(token):
    """Para la pantalla de 'preparando tu sistema'."""
    fila = registro.buscar_por_token(token)
    if fila is None:
        return jsonify({"error": "El enlace no es valido."}), 404

    return jsonify({
        "estado": fila["estado"],
        "slug": fila["slug"],
        "url": _url_consultorio(fila["slug"]) if fila["estado"] == "listo" else None,
    })
