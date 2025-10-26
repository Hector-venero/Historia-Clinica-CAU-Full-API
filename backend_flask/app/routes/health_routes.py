# backend_flask/app/routes/health_routes.py
from flask import Blueprint, jsonify
import mysql.connector
import smtplib
import requests
from flask_login import current_user, login_required
from app.config import Config

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
        "bfa_node": "unknown",
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

    # ✅ Verificar nodo BFA (Geth)
    try:
        bfa_url = "http://bfa-node:8545"
        response = requests.post(
            bfa_url,
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            timeout=3
        )
        if response.ok and "result" in response.json():
            status["bfa_node"] = "reachable"
        else:
            status["bfa_node"] = "no response"
            status["status"] = "degraded"
    except Exception as e:
        status["bfa_node"] = f"error: {str(e)}"
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
