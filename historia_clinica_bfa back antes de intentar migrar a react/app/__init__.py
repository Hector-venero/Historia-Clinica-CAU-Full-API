from flask import Flask, jsonify
import json
from flask_login import LoginManager
from .auth import Usuario
from .database import get_connection
from datetime import timedelta
from flask_mail import Mail
from flask_cors import CORS

# -------------------------
# Crear app
# -------------------------
app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = '2908'
app.jinja_env.filters['from_json'] = json.loads
app.permanent_session_lifetime = timedelta(hours=1)

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
            id=data['id'],
            nombre=data['nombre'],
            username=data['username'],
            email=data['email'],
            password_hash=data['password_hash'],
            rol=data['rol']
        )
    return None

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'No autorizado'}), 401

# -------------------------
# Configuración Mail
# -------------------------
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='hectorvenero2908@gmail.com',
    MAIL_PASSWORD='typyayxujklnyskg',
    MAIL_DEFAULT_SENDER='hectorvenero29hv@gmail.com'
)

mail = Mail(app)

# -------------------------
# Importar y registrar Blueprints
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

# Registrar blueprints
app.register_blueprint(bp_auth)        # -> /api/login, /api/logout
app.register_blueprint(bp_usuarios)    # -> /api/usuarios
app.register_blueprint(bp_pacientes)   # -> /api/pacientes
app.register_blueprint(bp_historias)   # -> /api/pacientes/<id>/historias
app.register_blueprint(bp_turnos)      # -> /api/turnos
app.register_blueprint(bp_ausencias)   # -> /api/ausencias
app.register_blueprint(bp_dashboard)   # -> /api/dashboard
app.register_blueprint(bp_disponibilidades)
app.register_blueprint(bp_grupos)
