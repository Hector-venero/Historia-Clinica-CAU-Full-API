"""Recetas electronicas y prescripcion de estudios.

Fusion de las dos implementaciones que existian en paralelo. La estructura y las
reglas de negocio vienen del fork (validaciones, split receta/estudio,
persistencia local); anular receta, envio por mail, busqueda de paciente y el
registro automatico de la evolucion vienen de esta rama.

Dos cosas que estaban hardcodeadas y ahora no:

- El lugar de atencion (nombre del consultorio, domicilio y email) salia de una
  constante en el codigo, duplicada ademas en el frontend. Ahora sale de las
  columnas `lugar_atencion_*` del profesional, que es lo que la receta tiene que
  declarar: donde atiende quien la firma.
- La URL del proveedor ya no tiene default. Apuntaba al ambiente de
  homologacion, asi que olvidar la variable en produccion emitia recetas contra
  el ambiente de pruebas en silencio.
"""

import json
from datetime import date, datetime

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from flask_mail import Message

from app.database import db_cursor
from app.utils import qbi_client
from app.utils.permisos import requiere_rol
from app.utils.validacion import validar_email

bp_recetas = Blueprint("recetas", __name__, url_prefix="/api/recetas")

TIPOS_VALIDOS = {"receta", "estudio"}
MAX_MEDICAMENTOS = 3
MAX_CANTIDAD_POR_MEDICAMENTO = 2


# ---------------------------------------------------------------- helpers


def _error_qbi(exc):
    """Traduce un fallo del proveedor a una respuesta HTTP."""
    if isinstance(exc, qbi_client.QbiNoConfigurado):
        return jsonify({"error": str(exc)}), 503
    return jsonify({"error": str(exc), "detalle": exc.detalle}), exc.status


def _sexo_qbi(sexo):
    mapa = {
        "masculino": "M", "femenino": "F", "otro": "X",
        "m": "M", "f": "F", "x": "X", "o": "O",
    }
    return mapa.get((sexo or "").strip().lower(), "X")


def _sin_vacios(valor):
    """Poda claves vacias: el proveedor rechaza campos presentes pero nulos."""
    if isinstance(valor, dict):
        return {k: _sin_vacios(v) for k, v in valor.items() if v not in (None, "", [], {})}
    if isinstance(valor, list):
        return [_sin_vacios(v) for v in valor if v not in (None, "", [], {})]
    return valor


def _partir_nombre(nombre_completo):
    partes = (nombre_completo or "").strip().split()
    if len(partes) <= 1:
        return (partes[0] if partes else ""), ""
    return " ".join(partes[:-1]), partes[-1]


def _traer(tabla, id_):
    with db_cursor() as (_conn, cursor):
        cursor.execute(f"SELECT * FROM {tabla} WHERE id = %s", (id_,))
        return cursor.fetchone()


def _construir_medico(usuario):
    """Bloque `medico` de la receta, armado desde el usuario que la firma."""
    nombre, apellido = _partir_nombre(usuario.get("nombre"))
    # `apellido` propio gana sobre el deducido del nombre completo.
    apellido = usuario.get("apellido") or apellido
    especialidad = usuario.get("especialidad") or usuario.get("profesion")
    return {
        "apellido": apellido,
        "nombre": nombre,
        "tipoDoc": "DNI",
        "nroDoc": usuario.get("dni"),
        "sexo": _sexo_qbi(usuario.get("sexo")),
        "especialidad": especialidad,
        "email": usuario.get("email"),
        "telefono": usuario.get("telefono"),
        "matricula": {
            "tipo": usuario.get("matricula_tipo") or "MN",
            "numero": usuario.get("matricula_numero"),
            "provincia": usuario.get("matricula_provincia"),
            "especialidad": especialidad,
        },
    }


def _construir_lugar_atencion(usuario):
    """Lugar de atencion del profesional. Antes era una constante en el codigo."""
    return {
        "nombreConsultorio": usuario.get("lugar_atencion_nombre"),
        "email": usuario.get("lugar_atencion_email") or usuario.get("email"),
        "telefono": usuario.get("lugar_atencion_contacto") or usuario.get("telefono"),
        "domicilio": {
            "direccion": usuario.get("lugar_atencion_direccion"),
            "pais": "Argentina",
        },
    }


def _diagnostico(data, fallback=None):
    cfg = current_app.config
    origen = fallback or {}
    codigo = (
        data.get("codigoDiagnostico")
        or origen.get("codigoDiagnostico")
        or cfg["RECETA_DIAGNOSTICO_CODIGO"]
    )
    texto = (
        data.get("diagnostico")
        or origen.get("diagnostico")
        or cfg["RECETA_DIAGNOSTICO_TEXTO"]
    )
    return str(codigo).strip(), str(texto).strip()


def _observaciones(data, fallback=None):
    origen = fallback or {}
    valor = (
        data.get("observaciones")
        or origen.get("observaciones")
        or current_app.config["RECETA_OBSERVACION"]
    )
    return str(valor).strip()


def _payload_comun(data, paciente, usuario, client_id):
    cobertura = data.get("cobertura") or {}
    return _sin_vacios({
        "clienteAppId": client_id,
        "paciente": {
            "apellido": paciente.get("apellido"),
            "nombre": paciente.get("nombre"),
            "tipoDoc": data.get("paciente_tipo_doc") or "DNI",
            "nroDoc": paciente.get("dni"),
            "sexo": _sexo_qbi(paciente.get("sexo")),
            "fechaNacimiento": paciente.get("fecha_nacimiento"),
            "email": paciente.get("email"),
            "telefono": paciente.get("celular") or paciente.get("telefono"),
            "cobertura": {
                "idFinanciador": cobertura.get("idFinanciador"),
                "plan": cobertura.get("plan"),
                "planId": cobertura.get("planId"),
                "numero": cobertura.get("numero"),
                "dniTitular": cobertura.get("dniTitular"),
            },
            "domicilio": {
                "direccion": paciente.get("direccion"),
                "codigoPostal": paciente.get("codigo_postal"),
                "provincia": data.get("paciente_provincia"),
                "pais": "Argentina",
            },
        },
        "medico": _construir_medico(usuario),
        "lugarAtencion": _construir_lugar_atencion(usuario),
    })


def _payload_receta(data, paciente, usuario, client_id):
    codigo, texto = _diagnostico(data)
    payload = _payload_comun(data, paciente, usuario, client_id)
    payload.update({
        "medicamentos": data.get("medicamentos") or [],
        "diagnostico": texto,
        "codigoDiagnostico": codigo,
        "indicaciones": data.get("indicaciones"),
        "observaciones": _observaciones(data),
        "imprimirDiagnostico": data.get("imprimirDiagnostico") or "S",
    })
    return _sin_vacios(payload)


def _payload_estudio(data, paciente, usuario, client_id, estudio):
    codigo, texto = _diagnostico(estudio, fallback=data)
    observaciones = _observaciones(estudio, fallback=data)
    payload = _payload_comun(data, paciente, usuario, client_id)
    payload.update({
        "prescripcion": [{
            "nombre": (estudio.get("texto") or estudio.get("nombre") or "").strip(),
            "diagnostico": texto,
            "codigoDiagnostico": codigo,
            "observaciones": observaciones,
        }],
        "diagnostico": texto,
        "codigoDiagnostico": codigo,
        "indicaciones": data.get("indicaciones"),
        "observaciones": observaciones,
        "imprimirDiagnostico": data.get("imprimirDiagnostico") or "S",
    })
    return _sin_vacios(payload)


# ---------------------------------------------------------------- validacion


def _validar_medicamentos(medicamentos):
    if not medicamentos:
        return "Agregue al menos un medicamento."
    if len(medicamentos) > MAX_MEDICAMENTOS:
        return f"Cada receta admite como máximo {MAX_MEDICAMENTOS} medicamentos distintos."
    for i, med in enumerate(medicamentos, start=1):
        try:
            cantidad = int(med.get("cantidad") or 0)
        except (TypeError, ValueError):
            return f"La cantidad del medicamento {i} debe ser numérica."
        if not 1 <= cantidad <= MAX_CANTIDAD_POR_MEDICAMENTO:
            return f"La cantidad del medicamento {i} debe estar entre 1 y {MAX_CANTIDAD_POR_MEDICAMENTO}."
        if not (med.get("regNo") or med.get("nombreProducto")):
            return f"Complete el medicamento {i}."
    return None


def _validar_estudios(estudios):
    if not estudios:
        return "Agregue al menos un estudio."
    for i, estudio in enumerate(estudios, start=1):
        if not (estudio.get("texto") or estudio.get("nombre") or "").strip():
            return f"Complete el texto libre del estudio {i}."
    return None


def _validar_payload(payload):
    """Datos obligatorios para que el proveedor acepte la receta.

    Se chequean acá para devolver un mensaje que diga qué falta y dónde
    completarlo. Sin esto, el proveedor rechaza con códigos como QBI240
    ("debe ingresar calle y número"), que no indican de quién es el domicilio
    ni en qué pantalla se carga.
    """
    medico = payload.get("medico") or {}
    matricula = medico.get("matricula") or {}
    paciente = payload.get("paciente") or {}

    if not medico.get("nombre") or not medico.get("apellido") or not medico.get("nroDoc"):
        return "Complete nombre, apellido y DNI del profesional en su perfil."
    if not matricula.get("numero"):
        return "Complete la matrícula del profesional en su perfil."
    if not payload.get("lugarAtencion", {}).get("domicilio", {}).get("direccion"):
        return "Complete la dirección del lugar de atención en su perfil."

    # El domicilio del paciente también es obligatorio para el proveedor.
    if not paciente.get("domicilio", {}).get("direccion"):
        return "Complete el domicilio del paciente en su ficha antes de emitir la receta."
    if not paciente.get("nroDoc"):
        return "Complete el DNI del paciente en su ficha antes de emitir la receta."

    return None


# ---------------------------------------------------------------- persistencia


def _guardar_receta(cursor, paciente_id, payload, respuesta, *, tipo, endpoint):
    recetas = respuesta.get("recetas") or []
    primera = recetas[0] if recetas else {}
    bloque = respuesta.get("response") or []
    estado = (bloque[0] or {}).get("status") if bloque else "emitida"

    cursor.execute(
        """
        INSERT INTO recetas_electronicas (
            paciente_id, usuario_id, tipo, qbitos_endpoint, qbitos_id_receta,
            qbitos_s3_link, qbitos_verificador, id_transaccion, estado,
            afiliado_numero, request_json, response_json, creado_en, actualizado_en
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            paciente_id,
            current_user.id,
            tipo,
            endpoint,
            primera.get("idReceta") or primera.get("id"),
            primera.get("s3Link"),
            primera.get("verificador"),
            respuesta.get("idTransaccion"),
            estado,
            (payload.get("paciente", {}).get("cobertura", {}) or {}).get("numero"),
            json.dumps(payload, ensure_ascii=False),
            json.dumps(respuesta, ensure_ascii=False),
            datetime.now(),
            datetime.now(),
        ),
    )
    return cursor.lastrowid, primera


def _registrar_evolucion(cursor, paciente_id, descripcion):
    """Deja constancia en la historia clinica de lo prescripto.

    Una receta es un acto medico: tiene que quedar en la evolucion del paciente,
    no solo en la tabla del modulo.
    """
    cursor.execute(
        "INSERT INTO evoluciones (paciente_id, fecha, contenido, usuario_id) VALUES (%s, %s, %s, %s)",
        (paciente_id, date.today(), descripcion, current_user.id),
    )


def _enviar_email_receta(email, nombre_paciente, link_pdf, detalle):
    doctor = getattr(current_user, "apellido", None) or current_user.nombre
    html = f"""
    <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
    <p>El/La Dr./Dra. <strong>{doctor}</strong> le ha emitido una receta
       electrónica para <strong>{detalle}</strong>.</p>
    <p>
      <a href="{link_pdf}"
         style="background:#2563eb;color:#fff;padding:10px 20px;
                border-radius:6px;text-decoration:none;display:inline-block;">
        Descargar Receta
      </a>
    </p>
    <p style="color:#6b7280;font-size:12px;">
      Este mensaje fue generado automáticamente. No responda a este correo.
    </p>
    """
    current_app.extensions["mail"].send(
        Message(subject="Tu Receta Médica Electrónica", recipients=[email], html=html)
    )


# ---------------------------------------------------------------- rutas


@bp_recetas.get("/config")
@login_required
def config_recetas():
    """Permite al frontend saber si el módulo está operativo antes de mostrarlo."""
    if not qbi_client.esta_configurado():
        return jsonify({"configured": False}), 503
    config = qbi_client.get_config()
    return jsonify({
        "configured": True,
        "clientAppId": config["client_id"],
        "baseUrl": config["base_url"],
    })


@bp_recetas.get("/buscar_paciente")
@login_required
def buscar_paciente():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify([])

    like = f"%{q}%"
    with db_cursor() as (_conn, cursor):
        cursor.execute(
            """SELECT id, nombre, apellido, dni, sexo, fecha_nacimiento, cobertura, email
               FROM pacientes
               WHERE dni LIKE %s OR nombre LIKE %s OR apellido LIKE %s
               LIMIT 20""",
            (like, like, like),
        )
        filas = cursor.fetchall()

    for fila in filas:
        if fila.get("fecha_nacimiento"):
            fila["fecha_nacimiento"] = str(fila["fecha_nacimiento"])
    return jsonify(filas)


@bp_recetas.get("/financiadores")
@login_required
def listar_financiadores():
    try:
        return jsonify(qbi_client.get_financiadores())
    except (qbi_client.QbiError, qbi_client.QbiNoConfigurado) as exc:
        return _error_qbi(exc)


@bp_recetas.get("/buscar_medicamento")
@bp_recetas.get("/medicamentos")
@login_required
def buscar_medicamentos():
    texto = (request.args.get("q") or "").strip()
    if len(texto) < 2:
        return jsonify({"error": "Ingrese al menos 2 caracteres"}), 400

    filtros = {
        clave: request.args.get(clave)
        for clave in ("idFinanciador", "afiliadoDni", "afiliadoCredencial", "planid", "plan")
    }
    filtros["numeroPagina"] = request.args.get("numeroPagina", 1)

    try:
        return jsonify(qbi_client.buscar_medicamento(texto, **filtros))
    except (qbi_client.QbiError, qbi_client.QbiNoConfigurado) as exc:
        return _error_qbi(exc)


@bp_recetas.get("/buscar_diagnostico")
@bp_recetas.get("/diagnosticos")
@login_required
def buscar_diagnosticos():
    texto = (request.args.get("q") or "").strip()
    if len(texto) < 3:
        return jsonify({"error": "Ingrese al menos 3 caracteres"}), 400
    try:
        return jsonify(qbi_client.buscar_diagnostico(texto))
    except (qbi_client.QbiError, qbi_client.QbiNoConfigurado) as exc:
        return _error_qbi(exc)


@bp_recetas.delete("/anular/<hash_receta>")
@login_required
@requiere_rol("director", "profesional")
def anular(hash_receta):
    try:
        respuesta = qbi_client.anular_receta(hash_receta)
    except (qbi_client.QbiError, qbi_client.QbiNoConfigurado) as exc:
        return _error_qbi(exc)

    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE recetas_electronicas SET estado = 'anulada', actualizado_en = NOW() "
            "WHERE qbitos_id_receta = %s",
            (hash_receta,),
        )
        conn.commit()

    return jsonify(respuesta)


@bp_recetas.post("/enviar_mail_manual")
@login_required
def enviar_mail_manual():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip()
    link_pdf = body.get("link_pdf") or ""

    if not email or not validar_email(email):
        return jsonify({"error": "Email inválido o ausente"}), 400
    if not link_pdf:
        return jsonify({"error": "Falta el link del PDF"}), 400

    try:
        _enviar_email_receta(
            email,
            body.get("nombre_paciente", ""),
            link_pdf,
            body.get("nombre_med", "su prescripción"),
        )
    except Exception as exc:
        current_app.logger.exception("Fallo el envío del mail de receta")
        return jsonify({"error": f"No se pudo enviar el mail: {exc}"}), 502

    return jsonify({"ok": True})


@bp_recetas.post("")
@bp_recetas.post("/emitir")
@login_required
@requiere_rol("director", "profesional")
def emitir():
    """Emite una receta de medicamentos o una prescripción de estudios.

    Los estudios se emiten de a uno: el proveedor expone un endpoint distinto y
    cada bloque de texto libre es una prescripción independiente.
    """
    data = request.get_json(silent=True) or {}
    tipo = (data.get("tipo") or "receta").strip().lower()
    paciente_id = data.get("paciente_id")

    if not paciente_id:
        return jsonify({"error": "paciente_id es obligatorio"}), 400
    if tipo not in TIPOS_VALIDOS:
        return jsonify({"error": "tipo debe ser receta o estudio"}), 400

    if not qbi_client.esta_configurado():
        return jsonify({"error": "Integración de recetas no configurada"}), 503
    client_id = qbi_client.get_config()["client_id"]

    paciente = _traer("pacientes", paciente_id)
    if not paciente:
        return jsonify({"error": "Paciente no encontrado"}), 404
    if paciente.get("fecha_nacimiento") and hasattr(paciente["fecha_nacimiento"], "strftime"):
        paciente["fecha_nacimiento"] = paciente["fecha_nacimiento"].strftime("%Y-%m-%d")

    usuario = _traer("usuarios", current_user.id) or {}

    if tipo == "receta":
        return _emitir_receta(data, paciente, usuario, client_id)
    return _emitir_estudios(data, paciente, usuario, client_id)


def _emitir_receta(data, paciente, usuario, client_id):
    medicamentos = data.get("medicamentos") or []
    error = _validar_medicamentos(medicamentos)
    if error:
        return jsonify({"error": error}), 400

    payload = _payload_receta(data, paciente, usuario, client_id)
    error = _validar_payload(payload)
    if error:
        return jsonify({"error": error}), 400

    try:
        respuesta = qbi_client.emitir_receta(payload)
    except (qbi_client.QbiError, qbi_client.QbiNoConfigurado) as exc:
        return _error_qbi(exc)

    detalle = ", ".join(
        m.get("nombreProducto") or m.get("regNo") or "" for m in medicamentos
    ).strip(", ")

    with db_cursor() as (conn, cursor):
        receta_id, primera = _guardar_receta(
            cursor, paciente["id"], payload, respuesta,
            tipo="receta", endpoint=qbi_client.RECETA_ENDPOINT,
        )
        _registrar_evolucion(
            cursor,
            paciente["id"],
            f"Se emitió receta electrónica Nro: {primera.get('idReceta') or primera.get('id')}. "
            f"Medicamentos: {detalle}.",
        )
        conn.commit()

    _quizas_enviar_mail(data, paciente, primera, detalle)

    return jsonify({
        "message": "Receta emitida correctamente",
        "id": receta_id,
        "receta_hash": primera.get("idReceta") or primera.get("id"),
        "link_pdf": primera.get("s3Link"),
        "qbitos": respuesta,
    })


def _emitir_estudios(data, paciente, usuario, client_id):
    estudios = data.get("estudios") or []
    error = _validar_estudios(estudios)
    if error:
        return jsonify({"error": error}), 400

    resultados = []
    for indice, estudio in enumerate(estudios):
        payload = _payload_estudio(data, paciente, usuario, client_id, estudio)
        error = _validar_payload(payload)
        if error:
            return jsonify({"error": error, "estudioIndex": indice}), 400

        try:
            respuesta = qbi_client.emitir_practica(payload)
        except (qbi_client.QbiError, qbi_client.QbiNoConfigurado) as exc:
            # Los estudios ya emitidos quedan emitidos: se informa hasta dónde
            # se llegó en vez de fingir que no pasó nada.
            cuerpo, status = _error_qbi(exc)
            cuerpo.json["estudioIndex"] = indice
            cuerpo.json["emitidos"] = resultados
            return cuerpo, status

        with db_cursor() as (conn, cursor):
            receta_id, primera = _guardar_receta(
                cursor, paciente["id"], payload, respuesta,
                tipo="estudio", endpoint=qbi_client.PRACTICA_ENDPOINT,
            )
            _registrar_evolucion(
                cursor,
                paciente["id"],
                f"Se prescribió estudio: {estudio.get('texto') or estudio.get('nombre')}.",
            )
            conn.commit()

        resultados.append({
            "id": receta_id,
            "receta_hash": primera.get("idReceta") or primera.get("id"),
            "link_pdf": primera.get("s3Link"),
            "estudioIndex": indice,
            "qbitos": respuesta,
        })

    return jsonify({"message": "Estudios emitidos correctamente", "resultados": resultados})


def _quizas_enviar_mail(data, paciente, primera, detalle):
    """Envia la receta por mail si hay direccion. Nunca hace fallar la emision."""
    email = (data.get("email_paciente") or paciente.get("email") or "").strip()
    link = primera.get("s3Link")
    if not email or not link or not validar_email(email):
        return
    try:
        _enviar_email_receta(email, paciente.get("nombre", ""), link, detalle)
    except Exception:
        current_app.logger.exception("La receta se emitió pero falló el envío del mail")
