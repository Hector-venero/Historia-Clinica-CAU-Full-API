"""El portal del paciente: entrar, ver lo que le enviaron y descargarlo.

Atiende en el subdominio reservado del portal (`mi.<dominio>`), no en el de un
consultorio. Por eso `tenancy` lo exime de resolver inquilino: un paciente no
pertenece a ningun consultorio, y justamente lo que se busca es que vea junto lo
que le mandaron varios.

**Todo lo de aca es de solo lectura sobre el plano del paciente.** No hay una
sola consulta a una base clinica: lo que el paciente ve es lo que alguien
decidio enviarle, ya copiado a su buzon.
"""

import os
from functools import wraps

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_login import current_user, login_required, login_user, logout_user

from app import portal
from app.utils.correo import enviar_en_segundo_plano
from app.utils.mails_portal import mail_bienvenida_paciente, mail_verificacion_paciente

bp_portal = Blueprint("portal", __name__, url_prefix="/api/portal")


def requiere_paciente(f):
    """Exige que quien pide sea un paciente, no personal de un consultorio.

    Sin esto, la sesion de un director de consultorio —valida y autenticada—
    entraria al portal, y `current_user` no tendria documento con el cual buscar
    su buzon. Fallaria con un AttributeError en vez de con un 403 claro.
    """
    @wraps(f)
    def envoltorio(*args, **kwargs):
        if not getattr(current_user, "es_paciente", False):
            return jsonify({"error": "Esta seccion es para pacientes."}), 403
        return f(*args, **kwargs)

    return envoltorio


def _url_portal():
    dominio = (current_app.config.get("DOMINIO_BASE") or "").strip().strip(".")
    if not dominio:
        return "http://mi.localhost:5173"
    esquema = "https" if current_app.config.get("ENV") == "production" else "http"
    return f"{esquema}://mi.{dominio}"


# ------------------------------------------------------------------ registro


@bp_portal.post("/registro")
def registro():
    """Guarda la intencion de alta y manda el correo de verificacion."""
    datos = request.get_json(silent=True) or {}

    try:
        token = portal.registrar(datos)
    except portal.ErrorPortal as exc:
        return jsonify({"error": str(exc)}), 400

    mensaje = mail_verificacion_paciente(
        destinatario=(datos.get("email") or "").strip().lower(),
        nombre=(datos.get("nombre") or "").strip(),
        token=token,
        url_portal=_url_portal(),
    )
    if mensaje is not None:
        enviar_en_segundo_plano(mensaje)

    return jsonify({
        "mensaje": "Te mandamos un correo para confirmar tu direccion.",
    }), 202


@bp_portal.post("/verificar/<token>")
def verificar(token):
    """Confirma el correo, crea la cuenta e inicia sesion."""
    try:
        paciente = portal.verificar_registro(token)
    except portal.ErrorPortal as exc:
        return jsonify({"error": str(exc)}), 400

    if paciente is None:
        return jsonify({"error": "No pudimos crear tu cuenta."}), 500

    login_user(paciente)

    mensaje = mail_bienvenida_paciente(
        destinatario=paciente.email,
        nombre=paciente.nombre,
        url_portal=_url_portal(),
    )
    if mensaje is not None:
        enviar_en_segundo_plano(mensaje)

    return jsonify({"mensaje": "Cuenta creada", "paciente": paciente.a_json()})


# -------------------------------------------------------------------- sesion


@bp_portal.post("/login")
def login():
    datos = request.get_json(silent=True) or {}
    paciente = portal.autenticar(datos.get("email"), datos.get("password"))

    if paciente is None:
        # Mismo mensaje para "no existe" y "clave incorrecta": distinguirlos deja
        # averiguar que correos estan registrados.
        return jsonify({"error": "Correo o contrasena incorrectos."}), 401

    login_user(paciente)
    return jsonify({"paciente": paciente.a_json()})


@bp_portal.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"mensaje": "Sesion cerrada"})


@bp_portal.get("/me")
@login_required
@requiere_paciente
def me():
    return jsonify(current_user.a_json())


@bp_portal.post("/perfil")
@login_required
@requiere_paciente
def actualizar_perfil():
    datos = request.get_json(silent=True) or {}
    paciente = portal.actualizar_perfil(current_user.id, datos)
    return jsonify(paciente.a_json())


# --------------------------------------------------------------------- buzon


@bp_portal.get("/documentos")
@login_required
@requiere_paciente
def documentos():
    """Todo lo que le enviaron, de todos los consultorios."""
    filas = portal.documentos_de(
        current_user.tipo_documento, current_user.numero_documento
    )

    for fila in filas:
        # El token del archivo no viaja: la descarga va por id, y el id ya se
        # valida contra el dueño. Exponerlo permitiria armar la URL a mano.
        fila.pop("archivo_token", None)
        fila["tiene_archivo"] = bool(fila.pop("archivo_nombre", None)) or False

    return jsonify(filas)


@bp_portal.get("/documentos/sin_leer")
@login_required
@requiere_paciente
def documentos_sin_leer():
    return jsonify({
        "sin_leer": portal.sin_leer(
            current_user.tipo_documento, current_user.numero_documento
        )
    })


@bp_portal.post("/documentos/<int:documento_id>/leer")
@login_required
@requiere_paciente
def leer(documento_id):
    portal.marcar_leido(
        documento_id, current_user.tipo_documento, current_user.numero_documento
    )
    return jsonify({"mensaje": "Marcado como leido"})


@bp_portal.get("/documentos/<int:documento_id>/archivo")
@login_required
@requiere_paciente
def archivo(documento_id):
    """Descarga el adjunto, si el documento es de quien lo pide.

    La pertenencia va en el WHERE de la consulta, no en una comprobacion
    posterior: asi no hay forma de escribirla al reves por accidente.
    """
    documento = portal.documento_de(
        documento_id, current_user.tipo_documento, current_user.numero_documento
    )

    if documento is None or not documento.get("archivo_token"):
        # Mismo 404 para "no existe" y "no es tuyo": distinguirlos deja
        # averiguar que documentos existen probando numeros.
        return jsonify({"error": "No encontrado"}), 404

    from app.utils.adjuntos import carpeta_portal

    carpeta = str(carpeta_portal(documento["archivo_token"]))
    if not os.path.isdir(carpeta):
        return jsonify({"error": "No encontrado"}), 404

    return send_from_directory(
        carpeta, documento["archivo_nombre"], as_attachment=True
    )
