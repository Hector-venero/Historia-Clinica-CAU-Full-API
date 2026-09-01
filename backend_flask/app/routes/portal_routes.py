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


# ------------------------------------------------------ turnos online

@bp_portal.get("/profesionales")
def profesionales():
    """Directorio de quienes aceptan turnos online.

    **Sin sesion**: alguien tiene que poder ver con quien puede atenderse antes
    de decidir si se registra. Devuelve solo lo que el profesional publico
    explicitamente al activar su agenda.
    """
    from app import reservas

    filas = reservas.buscar_profesionales(
        texto=request.args.get("q"),
        especialidad=request.args.get("especialidad"),
    )
    return jsonify(filas)


@bp_portal.get("/especialidades")
def especialidades():
    from app import reservas

    return jsonify(reservas.especialidades_disponibles())


@bp_portal.get("/profesionales/<int:cliente_id>/<int:usuario_id>/servicios")
def servicios_del_profesional(cliente_id, usuario_id):
    """Las prestaciones que ofrece, para elegir antes que el horario.

    Sin sesion, como los horarios: saber que se puede pedir y cuanto sale es
    parte de decidir si vale la pena registrarse.

    Lista vacia si el consultorio no usa servicios. El portal lo trata como
    "elegis horario y nada mas", que es como funcionaba antes.
    """
    from app import reservas

    return jsonify({"servicios": reservas.servicios_publicos(cliente_id, usuario_id)})


@bp_portal.get("/profesionales/<int:cliente_id>/<int:usuario_id>/horarios")
def horarios(cliente_id, usuario_id):
    """Horarios libres de un profesional para un dia.

    Tambien sin sesion: ver si hay lugar es parte de decidir si vale la pena
    registrarse. Lo que exige cuenta es reservar.
    """
    from app import reservas

    try:
        libres = reservas.horarios_libres(
            cliente_id, usuario_id, request.args.get("fecha"),
            servicio_id=request.args.get("servicio_id", type=int),
        )
    except reservas.ErrorReserva as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"horarios": libres})


@bp_portal.get("/profesionales/<int:cliente_id>/<int:usuario_id>/proximo-dia")
def proximo_dia(cliente_id, usuario_id):
    """El primer dia con lugar, para no dejar a la persona adivinando.

    Sin sesion, como los horarios: es parte de decidir si vale la pena
    registrarse.
    """
    from app import reservas

    try:
        encontrado = reservas.proximo_dia_con_lugar(
            cliente_id, usuario_id, request.args.get("desde"),
            servicio_id=request.args.get("servicio_id", type=int),
        )
    except reservas.ErrorReserva as exc:
        return jsonify({"error": str(exc)}), 400

    # 200 con `dia: null` y no 404: que no haya lugar en las proximas dos
    # semanas es una respuesta valida a la pregunta, no un error del pedido.
    return jsonify({"dia": encontrado})


@bp_portal.post("/reservar")
@login_required
@requiere_paciente
def reservar():
    """Crea el turno. Es lo unico de esta seccion que exige cuenta.

    El turno se crea en la base del consultorio; el paciente vive en el plano del
    portal. Todo ese cruce esta encapsulado en app/reservas.py.
    """
    from app import reservas

    datos = request.get_json(silent=True) or {}

    # La conversion va afuera del try que atrapa los errores de reserva: si un
    # id no es numerico, eso es un pedido mal formado y no un horario ocupado.
    # Con las dos cosas en el mismo try, un TypeError de adentro se reportaba
    # como "datos incompletos" y ocultaba el error real.
    try:
        cliente_id = int(datos.get("cliente_id") or 0)
        usuario_id = int(datos.get("usuario_id") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "Datos incompletos."}), 400

    try:
        resultado = reservas.reservar(
            paciente=current_user,
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            fecha_inicio=datos.get("fecha_inicio"),
            motivo=datos.get("motivo"),
            servicio_id=datos.get("servicio_id"),
        )
    except reservas.ErrorReserva as exc:
        return jsonify({"error": str(exc)}), 409
    except Exception:
        current_app.logger.exception("Fallo la reserva de turno desde el portal")
        return jsonify({"error": "No pudimos confirmar el turno."}), 500

    return jsonify(resultado), 201


@bp_portal.get("/mis-turnos")
@login_required
@requiere_paciente
def mis_turnos():
    """Los turnos del paciente, verificados contra cada consultorio.

    No se confia en la copia del portal: si el consultorio cancelo el turno desde
    su sistema, el paciente tiene que verlo cancelado y no seguir contando con el.
    """
    from app import reservas
    from app.utils.fechas import a_iso_arg

    filas = reservas.mis_turnos(current_user)

    # Las fechas van en ISO con offset argentino, no con el jsonify por defecto.
    #
    # Ese serializa los DATETIME al formato de fecha HTTP **etiquetado como GMT**
    # aunque esten guardados en hora local, y el navegador los lee tres horas
    # corridos: un turno de las 14:00 se mostraria a las 11:00. Es exactamente el
    # mismo error que ya habia en /api/ausencias.
    for fila in filas:
        for campo in ("fecha_inicio", "creado_en", "cancelado_en"):
            if campo in fila:
                fila[campo] = a_iso_arg(fila[campo])

    return jsonify(filas)


@bp_portal.delete("/mis-turnos/<int:reserva_id>")
@login_required
@requiere_paciente
def cancelar_turno(reserva_id):
    """Cancela un turno. El horario queda libre para otro paciente en el acto."""
    from app import reservas

    try:
        reservas.cancelar(current_user, reserva_id)
    except reservas.ErrorReserva as exc:
        return jsonify({"error": str(exc)}), 409
    except Exception:
        current_app.logger.exception("Fallo la cancelacion desde el portal")
        return jsonify({"error": "No pudimos cancelar el turno."}), 500

    return jsonify({"mensaje": "Turno cancelado"})


# ------------------------------------------------- recuperar la contrasena

# Sal propia, distinta de la del personal (`reset-password` en auth_routes).
#
# La SECRET_KEY es la misma para toda la plataforma, asi que sin separar la sal
# un enlace de recuperacion emitido para un usuario de consultorio serviria en el
# portal y al reves: dos poblaciones distintas compartiendo tokens.
SAL_RESET_PACIENTE = "reset-password-paciente"

# Una hora, igual que para el personal. Suficiente para leer el correo y corto
# para que un enlace olvidado en la bandeja no sirva un mes despues.
VALIDEZ_RESET_SEGUNDOS = 3600


@bp_portal.post("/recuperar")
def recuperar():
    """Manda el enlace para restablecer la contrasena.

    **Responde lo mismo exista o no la cuenta.** El circuito del personal
    devuelve 404 cuando el correo no esta registrado, y aca eso seria peor: el
    formulario es publico, asi que cualquiera podria averiguar si una persona es
    paciente de la plataforma probando correos. Es informacion de salud.
    """
    from itsdangerous import URLSafeTimedSerializer

    from app.utils.mails_portal import mail_reset_paciente
    from app.utils.validacion import validar_email

    datos = request.get_json(silent=True) or {}
    email = (datos.get("email") or "").strip().lower()

    respuesta = jsonify({
        "mensaje": "Si ese correo tiene una cuenta, te mandamos el enlace.",
    })

    if not validar_email(email):
        return respuesta

    fila = portal.buscar_por_email(email)
    if fila:
        serializador = URLSafeTimedSerializer(current_app.secret_key)
        token = serializador.dumps(email, salt=SAL_RESET_PACIENTE)

        mensaje = mail_reset_paciente(
            destinatario=email,
            nombre=fila["nombre"],
            token=token,
            url_portal=_url_portal(),
        )
        if mensaje is not None:
            # En segundo plano: un SMTP lento no puede demorar la respuesta, y
            # ademas un tiempo de respuesta distinto segun exista o no la cuenta
            # delataria justo lo que el mensaje unico oculta.
            enviar_en_segundo_plano(mensaje)

    return respuesta


@bp_portal.post("/reset/<token>")
def reset(token):
    """Fija la contrasena nueva a partir del enlace del correo."""
    from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

    serializador = URLSafeTimedSerializer(current_app.secret_key)

    try:
        email = serializador.loads(
            token, salt=SAL_RESET_PACIENTE, max_age=VALIDEZ_RESET_SEGUNDOS
        )
    except SignatureExpired:
        return jsonify({"error": "El enlace vencio. Pedi uno nuevo."}), 400
    except BadSignature:
        return jsonify({"error": "El enlace no es valido."}), 400

    datos = request.get_json(silent=True) or {}
    nueva = datos.get("password") or ""
    repetida = datos.get("password_repetida") or ""

    if nueva != repetida:
        return jsonify({"error": "Las contrasenas no coinciden."}), 400

    fila = portal.buscar_por_email(email)
    if not fila:
        # La cuenta se dio de baja entre que se pidio el enlace y se uso.
        return jsonify({"error": "El enlace no es valido."}), 400

    try:
        portal.cambiar_password(fila["id"], nueva)
    except portal.ErrorPortal as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"mensaje": "Listo, ya podes entrar con tu contrasena nueva."})
