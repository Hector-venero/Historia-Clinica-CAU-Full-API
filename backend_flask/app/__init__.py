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
from app.database import db_cursor
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
app.config['DOMINIO_BASE'] = os.getenv("DOMINIO_BASE", "")

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
    """Resuelve la sesion a un usuario del personal o a un paciente.

    Son dos entidades distintas, en bases distintas, y el id 1 existe en las dos:
    el director de un consultorio y algun paciente. Por eso el identificador que
    viaja en la sesion lleva el prefijo `p:` cuando es un paciente.

    El prefijo se decide al iniciar sesion (`Paciente.get_id()`) y no se deduce
    del host: si dependiera del subdominio, un mismo identificador significaria
    cosas distintas segun por donde entrara el pedido.
    """
    if isinstance(user_id, str) and user_id.startswith("p:"):
        from app import portal

        try:
            return portal.buscar_por_id(int(user_id[2:]))
        except (ValueError, TypeError):
            return None

    with db_cursor() as (_conn, cursor):
        # activo = 1 tambien aca: sin el filtro, dar de baja a un usuario no
        # cerraba su sesion en curso, porque la cookie seguia resolviendo.
        cursor.execute(
            "SELECT * FROM usuarios WHERE id = %s AND activo = 1",
            (user_id,),
        )
        data = cursor.fetchone()

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
from app.routes.registro_routes import bp_registro
from app.routes.cuenta_routes import bp_cuenta
from app.routes.portal_routes import bp_portal
from app.routes.agenda_publica_routes import bp_agenda_publica
from app.routes.marca_routes import bp_marca
from app.routes.servicios_routes import bp_servicios

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
app.register_blueprint(bp_registro)
app.register_blueprint(bp_cuenta)
app.register_blueprint(bp_portal)
app.register_blueprint(bp_agenda_publica)
app.register_blueprint(bp_marca)
app.register_blueprint(bp_servicios)

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


# -------------------------
# Plataforma: suscripciones
# -------------------------
@app.cli.command("revisar-suscripciones")
@click.option("--dry-run", is_flag=True, help="Calcula sin avisar ni suspender.")
def revisar_suscripciones_command(dry_run):
    """Avisa a los que estan por vencer y suspende a los vencidos.

    Lo dispara un cron diario. Suspender corta el uso del sistema, no el acceso
    a los datos: el consultorio sigue pudiendo entrar y exportar sus historias.
    """
    from app import suscripcion

    resumen = suscripcion.revisar(dry_run=dry_run)
    click.echo(
        f"Avisados: {resumen['avisados']}. "
        f"Suspendidos: {resumen['suspendidos']}. "
        f"Errores: {resumen['errores']}."
    )
    if resumen["errores"]:
        raise click.ClickException("La revision termino con errores.")


@app.cli.command("clientes")
@click.option("--estado", default=None, help="Filtra por estado.")
def clientes_command(estado):
    """Lista los consultorios de la plataforma."""
    from app import plataforma, suscripcion

    filas = plataforma.listar([estado] if estado else None)
    if not filas:
        click.echo("No hay consultorios.")
        return

    click.echo(f"{'SLUG':<20} {'ESTADO':<12} {'PLAN':<10} {'PRUEBA HASTA':<14} ULTIMO ACCESO")
    for cliente in filas:
        dias = suscripcion.dias_restantes(cliente)
        vence = str(cliente.prueba_hasta or "-")
        if dias is not None:
            vence = f"{vence} ({dias}d)"
        click.echo(
            f"{cliente.slug:<20} {cliente.estado:<12} {cliente.plan:<10} "
            f"{vence:<14} {cliente.ultimo_acceso or '-'}"
        )


@app.cli.command("cliente-estado")
@click.argument("slug")
@click.argument("estado", type=click.Choice(["prueba", "activo", "suspendido", "cancelado"]))
@click.option("--motivo", default=None, help="Queda registrado para el soporte.")
def cliente_estado_command(slug, estado, motivo):
    """Cambia el estado de un consultorio.

    Cancelar NO borra la base: arranca el plazo de retencion.
    """
    from app import suscripcion

    if suscripcion.cambiar_estado(slug, estado, motivo) == 0:
        raise click.ClickException(f"No existe el consultorio '{slug}'.")
    click.echo(f"{slug}: {estado}")


@app.cli.command("cliente-plan")
@click.argument("slug")
@click.argument("plan", required=False)
@click.option("--modulos", default=None,
              help="Lista separada por comas que PISA lo que trae el plan. "
                   "Vacio ('') borra el override y vuelve a mandar el plan.")
def cliente_plan_command(slug, plan, modulos):
    """Muestra o cambia el plan de un consultorio.

    Sin PLAN solo informa. Es la unica forma que habia de cambiar los modulos
    sin escribir la base a mano.

    `--modulos` existe para venderle un modulo suelto a alguien sin inventar un
    plan nuevo por cada combinacion posible.
    """
    from app import marca, plataforma
    from app.tenancy import TTL_CACHE_SEGUNDOS, olvidar

    cliente = plataforma.buscar_por_slug(slug)
    if cliente is None:
        raise click.ClickException(f"No existe el consultorio '{slug}'.")

    if plan is None and modulos is None:
        incluidos = marca.PLANES.get(
            (cliente.plan or "").lower(), marca.PLANES[marca.PLAN_POR_DEFECTO]
        )
        propios = (cliente.config or {}).get("modulos")
        click.echo(f"{slug}: plan={cliente.plan}")
        click.echo(f"  el plan incluye : {', '.join(incluidos['modulos'])}")
        click.echo(f"  override         : {propios or '(ninguno)'}")
        return

    if plan is not None:
        if plan not in marca.PLANES:
            conocidos = ", ".join(sorted(marca.PLANES))
            raise click.ClickException(f"Plan desconocido. Conocidos: {conocidos}.")
        with plataforma.cursor_plataforma(commit=True) as (_conn, cur):
            cur.execute("UPDATE clientes SET plan = %s WHERE slug = %s", (plan, slug))

    if modulos is not None:
        limpios = [m.strip() for m in modulos.split(",") if m.strip()]
        desconocidos = set(limpios) - set(marca.MODULOS_CONOCIDOS)
        if desconocidos:
            raise click.ClickException(
                f"Modulos desconocidos: {', '.join(sorted(desconocidos))}."
            )
        # Vacio se guarda como '' y no como NULL: la columna es NOT NULL, y
        # `marca.modulos()` ya trata la cadena vacia como "sin override" — que
        # es distinto de "ningun modulo", con el que el consultorio se quedaria
        # sin sistema.
        plataforma.guardar_config(cliente.id, modulos=",".join(limpios))

    # El catalogo esta cacheado en memoria y este comando corre en otro proceso
    # que el servidor web: sin invalidar, el cambio tarda hasta el TTL.
    olvidar(slug)
    click.echo(f"{slug}: listo. Puede tardar hasta {TTL_CACHE_SEGUNDOS}s en verse.")


@app.cli.command("cancelados-vencidos")
def cancelados_vencidos_command():
    """Cancelados cuyo plazo de retencion ya paso.

    Solo los lista. Borrar la base de un consultorio con historias clinicas es
    irreversible y no puede ser el efecto secundario de una tarea automatica.
    """
    from app import suscripcion

    filas = suscripcion.cancelados_para_borrar()
    if not filas:
        click.echo(f"Ninguno supera los {suscripcion.DIAS_RETENCION} dias de retencion.")
        return

    click.echo(f"Cancelados hace mas de {suscripcion.DIAS_RETENCION} dias:")
    for fila in filas:
        click.echo(f"  {fila['slug']:<20} cancelado el {fila['cancelado_en']}  base={fila['db_nombre']}")
    click.echo("\nRevisalos y borralos a mano si corresponde.")


@app.cli.command("solicitudes")
def solicitudes_command():
    """Instituciones que esperan aprobacion.

    Reemplaza al formulario externo: la solicitud ya esta en el plano de control,
    asi que no hay que copiar datos de una planilla al sistema.
    """
    from app import registro

    filas = registro.solicitudes_pendientes()
    if not filas:
        click.echo("No hay solicitudes pendientes.")
        return

    for f in filas:
        click.echo(f"\n{'=' * 60}")
        click.echo(f"  {f['nombre']}   ({f['slug']})")
        click.echo(f"  Solicitada:    {f['creado_en']}")
        click.echo(f"  Contacto:      {f.get('contacto_nombre') or '-'}  {f.get('contacto_telefono') or ''}")
        click.echo(f"  Email:         {f['email']}")
        if f.get("localidad"):
            click.echo(f"  Donde:         {f.get('direccion') or ''} — {f['localidad']}")
        click.echo(f"  Profesionales: {f.get('cantidad_profesionales') or '?'}"
                   f"   Consultorios: {f.get('cantidad_consultorios') or '?'}")
        if f.get("atencion_online") is not None:
            click.echo(f"  Atencion online: {'si' if f['atencion_online'] else 'no'}")
        if f.get("sitio_web"):
            click.echo(f"  Sitio:         {f['sitio_web']}")
        if f.get("como_nos_conocio"):
            click.echo(f"  Nos conocio:   {f['como_nos_conocio']}")
        if f.get("comentarios"):
            click.echo(f"  Comentarios:   {f['comentarios']}")

    click.echo(f"\n{'=' * 60}")
    click.echo("Para aprobar:  flask aprobar-solicitud <slug>")
    click.echo("Para rechazar: flask rechazar-solicitud <slug> --motivo '...'")


@app.cli.command("aprobar-solicitud")
@click.argument("slug")
def aprobar_solicitud_command(slug):
    """Crea el consultorio de una institucion aprobada."""
    from app import registro
    from app.utils.correo import enviar_en_segundo_plano
    from app.utils.mails_registro import mail_bienvenida

    try:
        fila = registro.aprobar(slug)
    except registro.ErrorRegistro as exc:
        raise click.ClickException(str(exc))

    dominio = (os.getenv("DOMINIO_BASE") or "").strip().strip(".")
    url = f"https://{fila['slug']}.{dominio}" if dominio else f"http://{fila['slug']}.localhost:5173"

    mensaje = mail_bienvenida(destinatario=fila["email"], nombre=fila["nombre"], url=url)
    if mensaje is not None:
        enviar_en_segundo_plano(mensaje)

    click.echo(f"Aprobada: {fila['nombre']} -> {url}")
    click.echo("Entra con el usuario 'admin' y la contrasena que eligio al registrarse.")


@app.cli.command("rechazar-solicitud")
@click.argument("slug")
@click.option("--motivo", default=None, help="Queda registrado; no se envia automaticamente.")
def rechazar_solicitud_command(slug, motivo):
    """Marca una solicitud como rechazada.

    No borra nada: queda el registro de que alguien pidio una cuenta y por que no
    se le dio. Avisarle es una conversacion, no un correo automatico.
    """
    from app import registro

    if registro.rechazar(slug, motivo) == 0:
        raise click.ClickException(f"No hay solicitud pendiente para '{slug}'.")
    click.echo(f"Rechazada: {slug}")
