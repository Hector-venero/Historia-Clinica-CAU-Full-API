from flask import Flask, jsonify
import json
from flask_login import LoginManager
from flask_mail import Mail
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer
from flask_talisman import Talisman
from app.config import Config
from app.auth import Usuario
from app.database import get_connection
from datetime import timedelta

# -------------------------
# Crear app Flask
# -------------------------
app = Flask(__name__)
app.config.from_object(Config)

# Seguridad HTTP (headers CSP, HTTPS, etc.)
csp = {
    "default-src": ["'self'"],
    "img-src": ["'self'", "data:"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "script-src": ["'self'"]
}
Talisman(app, content_security_policy=csp)

# CORS (permite peticiones desde el frontend React)
CORS(app, supports_credentials=True, origins=["http://localhost:5173"])

# -------------------------
# Configuración Login
# -------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
    data = cursor.fetchone()
    conn.close()

    if data:
        return Usuario(
            id=data["id"],
            nombre=data["nombre"],
            username=data["username"],
            email=data["email"],
            password_hash=data["password_hash"],
            rol=data["rol"],
            duracion_turno = data.get("duracion_turno")

        )
    return None

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "No autorizado"}), 401

# -------------------------
# Configuración de correo (usa variables de entorno)
# -------------------------
mail = Mail(app)

# -------------------------
# Registrar Blueprints
# -------------------------
from app.routes.auth_routes import bp_auth
from app.routes.usuarios_routes import bp_usuarios
from app.routes.pacientes_routes import bp_pacientes
from app.routes.historias_routes import bp_historias
from app.routes.turnos_routes import bp_turnos
from app.routes.blockchain_routes import bp_blockchain
from app.routes.ausencias_routes import bp_ausencias
from app.routes.dashboard_routes import bp_dashboard
from app.routes.disponibilidades_routes import bp_disponibilidades
from app.routes.grupos_routes import bp_grupos
from app.routes.health_routes import bp_health

app.register_blueprint(bp_auth)
app.register_blueprint(bp_usuarios)
app.register_blueprint(bp_pacientes)
app.register_blueprint(bp_historias)
app.register_blueprint(bp_turnos)
app.register_blueprint(bp_ausencias)
app.register_blueprint(bp_dashboard)
app.register_blueprint(bp_disponibilidades)
app.register_blueprint(bp_grupos)
app.register_blueprint(bp_blockchain)
app.register_blueprint(bp_health)
