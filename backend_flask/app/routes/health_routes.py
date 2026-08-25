# backend_flask/app/routes/health_routes.py
from flask import Blueprint, jsonify
import mysql.connector
import smtplib
from flask_login import current_user, login_required
from app.config import Config
from app.utils.bfa_client import get_bfa_status

bp_health = Blueprint("bp_health", __name__, url_prefix="/api/health")

# ===========================================
# 🔓 Ruta pública — para monitores externos
# ===========================================
@bp_health.route("/public", methods=["GET"])
def public_health():
    """
    Endpoint simple que solo indica si la app responde.
    Ideal para servicios como UptimeRobot o Healthchecks.io
    """
    return jsonify({"status": "ok"}), 200


# ===========================================
# 🔐 Ruta privada — solo para Director
# ===========================================
@bp_health.route("/secure", methods=["GET"])
@login_required
def secure_health():
    """
    Endpoint detallado, accesible solo para usuarios con rol 'director'
    """
    if getattr(current_user, "rol", None) != "director":
        return jsonify({"error": "Acceso denegado"}), 403

    status = {
        "status": "ok",
        "database": "unknown",
        "bfa_tsa": "unknown",
        "mail": "unknown"
    }

    # ✅ Verificar conexión a la base de datos
    try:
        conn = mysql.connector.connect(
            host=Config.DB_CONFIG["host"],
            user=Config.DB_CONFIG["user"],
            password=Config.DB_CONFIG["password"],
            database=Config.DB_CONFIG["database"]
        )
        conn.close()
        status["database"] = "connected"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # ✅ Verificar la TSA de BFA
    # Antes esto le pegaba al nodo Geth local (http://bfa-node:8545), que dejo
    # de existir al migrar a la API oficial: el health quedaba degradado
    # permanentemente por un servicio que ya no forma parte del stack.
    try:
        bfa = get_bfa_status()
        if bfa.get("connected"):
            status["bfa_tsa"] = f"reachable ({bfa.get('tsa_url')})"
        else:
            status["bfa_tsa"] = f"error: {bfa.get('error', 'sin respuesta')}"
            status["status"] = "degraded"
    except Exception as e:
        status["bfa_tsa"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # ✅ Verificar servidor de correo SMTP
    try:
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=3)
        if Config.MAIL_USE_TLS:
            server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.quit()
        status["mail"] = "ready"
    except Exception as e:
        status["mail"] = f"error: {str(e)}"
        status["status"] = "degraded"

    return jsonify(status), (200 if status["status"] == "ok" else 503)
