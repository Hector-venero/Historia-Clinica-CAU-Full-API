import os
from datetime import date
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from flask_mail import Message
from app.database import get_connection
from app.utils.qbi_client import (
    buscar_medicamento, buscar_diagnostico, emitir_receta,
    get_financiadores, anular_receta,
)
from app.utils.validacion import validar_email

bp_recetas = Blueprint("recetas", __name__)

CLINICA_NOMBRE = "Consultorio Prueba"
CLINICA_CALLE = "San Martin"
CLINICA_NUMERO = "123"
CLINICA_CP = "1650"
CLINICA_LOCALIDAD = "San Martin"
CLINICA_PROVINCIA = "Buenos Aires"
CLINICA_PAIS = "AR"
CLINICA_EMAIL = "hectorvenero29hv@gmail.com"


# ---------------------------------------------------------------------------
# Búsqueda de pacientes en la BD local
# ---------------------------------------------------------------------------

@bp_recetas.route("/api/recetas/buscar_paciente", methods=["GET"])
@login_required
def get_buscar_paciente():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        like = f"%{q}%"
        cursor.execute(
            """SELECT id, nombre, apellido, dni, sexo, fecha_nacimiento, cobertura, email
               FROM pacientes
               WHERE dni LIKE %s OR nombre LIKE %s OR apellido LIKE %s
               LIMIT 20""",
            (like, like, like),
        )
        rows = cursor.fetchall()
        for row in rows:
            if row.get("fecha_nacimiento"):
                row["fecha_nacimiento"] = str(row["fecha_nacimiento"])
        return jsonify(rows)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Búsquedas QBI2
# ---------------------------------------------------------------------------

@bp_recetas.route("/api/recetas/buscar_medicamento", methods=["GET"])
@login_required
def get_medicamento():
    search = request.args.get("q", "").strip()
    if not search:
        return jsonify([])
    try:
        return jsonify(buscar_medicamento(search))
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@bp_recetas.route("/api/recetas/buscar_diagnostico", methods=["GET"])
@login_required
def get_diagnostico():
    search = request.args.get("q", "").strip()
    try:
        return jsonify(buscar_diagnostico(search))
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@bp_recetas.route("/api/recetas/financiadores", methods=["GET"])
@login_required
def get_lista_financiadores():
    try:
        return jsonify(get_financiadores())
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@bp_recetas.route("/api/recetas/anular/<hash_receta>", methods=["DELETE"])
@login_required
def delete_anular_receta(hash_receta):
    try:
        return jsonify(anular_receta(hash_receta))
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@bp_recetas.route("/api/recetas/enviar_mail_manual", methods=["POST"])
@login_required
def post_enviar_mail_manual():
    body = request.get_json() or {}
    email          = body.get("email", "")
    nombre_paciente = body.get("nombre_paciente", "")
    link_pdf       = body.get("link_pdf", "")
    nombre_med     = body.get("nombre_med", "")

    if not email or not validar_email(email):
        return jsonify({"error": "Email inválido o ausente"}), 400
    if not link_pdf:
        return jsonify({"error": "Falta el link del PDF"}), 400

    try:
        _enviar_email_receta(email, nombre_paciente, link_pdf, nombre_med)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ---------------------------------------------------------------------------
# Emisión de receta
# ---------------------------------------------------------------------------

@bp_recetas.route("/api/recetas/emitir", methods=["POST"])
@login_required
def post_emitir_receta():
    body        = request.get_json() or {}
    paciente    = body.get("paciente", {})
    medicamento = body.get("medicamento", {})
    diagnostico = body.get("diagnostico", {})

    paciente_id    = paciente.get("paciente_id")
    email_paciente = paciente.get("email_paciente", "")

    fecha_nac = paciente.get("fechaNacimiento", "")
    if "/" in fecha_nac:
        partes = fecha_nac.split("/")
        fecha_nac = f"{partes[2]}-{partes[1]}-{partes[0]}"

    id_financiador = paciente.get("idFinanciador")
    nro_afiliado   = paciente.get("nroAfiliado")

    paciente_payload = {
        "nombre":          paciente.get("nombre", ""),
        "apellido":        paciente.get("apellido", ""),
        "tipoDoc":         "DNI",
        "nroDoc":          paciente.get("nroDni", ""),
        "sexo":            paciente.get("sexo", ""),
        "fechaNacimiento": fecha_nac,
        "cuil":            "20401236547",
    }

    if id_financiador and nro_afiliado:
        paciente_payload["cobertura"] = {
            "idFinanciador": str(id_financiador),
            "numero":        str(nro_afiliado),
        }

    payload_qbi = {
        "clienteAppId": int(os.getenv("QBI_CLIENT_ID", "554")),
        "paciente": paciente_payload,
        "medico": {
            "nombre":    current_user.nombre,
            "apellido":  current_user.apellido or "",
            "tipoDoc":   "DNI",
            "nroDoc":    current_user.dni or "",
            "sexo":      current_user.sexo or "M",
            "profesion": current_user.profesion or "Médico",
            "matricula": {
                "tipo":      current_user.matricula_tipo or "MN",
                "numero":    current_user.matricula_numero or "",
                "provincia": current_user.matricula_provincia or "Nacional",
            },
        },
        "lugarAtencion": {
            "nombreConsultorio": CLINICA_NOMBRE,
            "domicilio": {
                "calle":        CLINICA_CALLE,
                "numero":       CLINICA_NUMERO,
                "codigoPostal": CLINICA_CP,
                "localidad":    CLINICA_LOCALIDAD,
                "municipio":    CLINICA_LOCALIDAD,
                "provincia":    CLINICA_PROVINCIA,
                "pais":         CLINICA_PAIS,
            },
            "email": CLINICA_EMAIL,
        },
        "medicamentos": [
            {
                "regNo":     medicamento.get("regNo", ""),
                "cantidad":  medicamento.get("cantidad", 1),
                "posologia": medicamento.get("posologia", ""),
            }
        ],
        "diagnostico": diagnostico.get("codigo", ""),
    }

    try:
        resultado   = emitir_receta(payload_qbi)
        receta_hash = resultado.get("recetas", [{}])[0].get("id")
        link_pdf    = resultado.get("recetas", [{}])[0].get("s3Link", "")

        nombre_med    = medicamento.get("nombre", medicamento.get("regNo", ""))
        posologia_med = medicamento.get("posologia", "")

        if paciente_id:
            _registrar_evolucion(paciente_id, receta_hash, nombre_med, posologia_med)

        if email_paciente and validar_email(email_paciente):
            _enviar_email_receta(
                email_paciente,
                paciente.get("nombre", ""),
                link_pdf,
                nombre_med,
            )

        return jsonify({**resultado, "receta_hash": receta_hash})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _registrar_evolucion(paciente_id, receta_hash, nombre_med, posologia):
    contenido = (
        f"Se emitió receta electrónica Nro: {receta_hash}. "
        f"Medicamento: {nombre_med}. "
        f"Posología: {posologia}."
    )
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO evoluciones (paciente_id, fecha, contenido, usuario_id) VALUES (%s, %s, %s, %s)",
            (paciente_id, date.today(), contenido, current_user.id),
        )
        conn.commit()
    finally:
        conn.close()


def _enviar_email_receta(email, nombre_paciente, link_pdf, nombre_med):
    doctor = current_user.apellido or current_user.nombre
    html_body = f"""
    <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
    <p>El/La Dr./Dra. <strong>{doctor}</strong> le ha emitido una receta
       electrónica para <strong>{nombre_med}</strong>.</p>
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
    msg = Message(
        subject="Tu Receta Médica Electrónica",
        recipients=[email],
        html=html_body,
    )
    current_app.extensions["mail"].send(msg)
