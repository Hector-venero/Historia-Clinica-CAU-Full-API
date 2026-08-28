from flask import Flask, jsonify
import json
import os

import click
from flask_login import LoginManager
from flask_mail import Mail
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer
from flask_talisman import Talisman
from app.config import Config
from app.auth import Usuario
from app.database import get_connection
from datetime import timedelta
from flask import send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix


def build_cors_origins(environment, frontend_url, configured_origins):
    """Arma la allowlist de CORS a partir del entorno.

    Reemplaza la lista de localhost hardcodeada, que en produccion dejaba
    entrar peticiones desde cualquier localhost. En produccion exige HTTPS
    y no admite otro origen que FRONTEND_URL, salvo que CORS_ORIGINS lo
    declare explicitamente.
    """
    environment = (environment or "development").strip().lower()
    frontend_url = (frontend_url or "").strip().rstrip("/")
    explicit_origins = [
        origin.strip().rstrip("/")
        for origin in (configured_origins or "").split(",")
        if origin.strip()
    ]

    if explicit_origins:
        return list(dict.fromkeys(explicit_origins))

    if environment == "production":
        if not frontend_url.startswith("https://"):
            raise RuntimeError("FRONTEND_URL debe ser una URL HTTPS en produccion.")
        return [frontend_url]

    return list(dict.fromkeys([
        frontend_url or "http://localhost",
        "http://localhost",
        "http://localhost:80",
        "http://localhost:5173",
        "http://localhost:4173",
    ]))


# -------------------------
# Crear app Flask
# -------------------------
app = Flask(__name__)
app.config.from_object(Config)
app.config['FRONTEND_URL'] = os.getenv("FRONTEND_URL", "http://localhost")

# Detras de nginx: sin esto Flask ve la IP y el esquema del proxy, no los del
# cliente, y arma mal las URLs absolutas y los chequeos de HTTPS.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Resolucion del consultorio por subdominio. Se registra antes que nada porque
# el cargador de usuario de Flask-Login consulta la base, y sin el cliente
# resuelto no sabria a cual. Sin MULTI_TENANT=true no hace nada y todo se
# comporta como una instalacion de un solo centro.
#
# La cookie de sesion se deja en el host exacto: NO se define
# SESSION_COOKIE_DOMAIN. Con un dominio comodin (.miproducto.com) la sesion de un
# consultorio viajaria a todos los demas.
from app.tenancy import registrar as registrar_tenancy  # noqa: E402

registrar_tenancy(app)

# Seguridad HTTP (headers CSP, HTTPS, etc.)
csp = {
    "default-src": ["'self'"],
    "img-src": ["'self'", "data:"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "script-src": ["'self'"]
}
# Seguridad HTTP (headers CSP, HTTPS según entorno)
env = os.getenv("FLASK_ENV", "development")
force_https = False #(env == "production")

Talisman(
    app,
    content_security_policy=None, 
    force_https=force_https
)


# CORS: allowlist derivada del entorno (ver build_cors_origins)
app.config['CORS_ORIGINS'] = build_cors_origins(
    environment=env,
    frontend_url=app.config['FRONTEND_URL'],
    configured_origins=os.getenv("CORS_ORIGINS", ""),
)
CORS(app, supports_credentials=True, origins=app.config['CORS_ORIGINS'])

# -------------------------
# Configuración Login
# -------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # activo = 1 tambien aca: sin el filtro, dar de baja a un usuario no
        # cerraba su sesion en curso, porque la cookie seguia resolviendo.
        cursor.execute(
            "SELECT * FROM usuarios WHERE id = %s AND activo = 1",
            (user_id,),
        )
        data = cursor.fetchone()
    finally:
        conn.close()

    return Usuario.desde_fila(data)

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
from app.routes.recetas_routes import bp_recetas
from app.routes.comunicados_routes import bp_comunicados
from app.routes.grupo_posteos_routes import bp_grupo_posteos
from app.routes.publico_routes import bp_publico

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
app.register_blueprint(bp_recetas)
app.register_blueprint(bp_comunicados)
app.register_blueprint(bp_grupo_posteos)
app.register_blueprint(bp_publico)

# -------------------------
# Servir fotos de usuario
# -------------------------
# Agregamos ambas rutas por seguridad (con y sin /api) para que funcione
# tanto si vas directo al backend como si pasas por el proxy.

# backend_flask/app/__init__.py

@app.route('/static/fotos_usuarios/<path:filename>')
@app.route('/api/static/fotos_usuarios/<path:filename>') 
def fotos_usuarios(filename):
    # Usamos la ruta absoluta segura basada en donde está este archivo
    basedir = os.path.abspath(os.path.dirname(__file__))
    carpeta = os.path.join(basedir, 'static', 'fotos_usuarios')
    
    # Debug para estar seguros
    print(f"🔍 Buscando: {filename}")
    print(f"📂 En carpeta: {carpeta}")
    
    return send_from_directory(carpeta, filename)


# -------------------------
# Comandos CLI
# -------------------------
@app.cli.command("enviar-alertas")
@click.option("--dry-run", is_flag=True, help="Calcula destinatarios y agendas sin enviar correos.")
def enviar_alertas_command(dry_run):
    """Manda a cada profesional el resumen de su agenda de manana.

    Lo dispara un cron diario (ver deploy/templates/). Con --dry-run calcula
    todo pero no envia, para poder verificar destinatarios sin molestar a nadie.
    """
    from app.utils.alertas import procesar_y_enviar_alertas

    resultado = procesar_y_enviar_alertas(dry_run=dry_run)
    click.echo(
        "Proceso finalizado. "
        f"Profesionales: {resultado['profesionales']}. "
        f"Enviados: {resultado['enviados']}. "
        f"Simulados: {resultado['simulados']}. "
        f"Errores: {resultado['errores']}."
    )
    # Exit code distinto de cero para que el cron detecte el fallo.
    if resultado["errores"]:
        raise click.ClickException("El proceso de alertas terminó con errores.")
