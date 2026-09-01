from flask import Blueprint, request, jsonify, session, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import marca
from app.auth import Usuario
from werkzeug.security import generate_password_hash
import secrets
from app import mail
from flask_mail import Message
from app.database import db_cursor
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.utils.validacion import password_valida, validar_email

bp_auth = Blueprint("auth", __name__)

def get_serializer():
    return URLSafeTimedSerializer(current_app.secret_key)

# =====================================================
# 1️⃣ LOGIN
# =====================================================
@bp_auth.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    # validación mínima
    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña son obligatorios'}), 400

    # Freno a la fuerza bruta. Esta pantalla de entrada es pública en cada
    # subdominio y del otro lado hay historias clínicas: sin esto, probar
    # `admin` contra las mil contraseñas más usadas es dejarlo corriendo.
    #
    # Va ANTES de tocar la base de usuarios: el punto es no hacer el trabajo.
    #
    # ⚠️ Se usa el `db_cursor` importado ARRIBA, a nivel de módulo, y no uno
    # importado acá adentro. Los tests enganchan la base falsa al módulo
    # (`make_db(monkeypatch, auth_routes)`), así que un import local se queda
    # con el real: la suite pasó de 0,7 s a 120 s intentando conectarse a MySQL.
    from app import antifuerzabruta

    ip = request.remote_addr
    try:
        antifuerzabruta.revisar(db_cursor, username, ip)
    except antifuerzabruta.DemasiadosIntentos as espera:
        # 429 y no 401: es una respuesta distinta y quien la lea tiene que poder
        # distinguirla, empezando por el propio frontend.
        return jsonify({'error': antifuerzabruta.mensaje(espera)}), 429

    user = Usuario.obtener_por_username(username)

    if user and user.verificar_password(password):
        antifuerzabruta.limpiar(db_cursor, username, ip)
        login_user(user)
        session.permanent = True
        return jsonify({
            'message': 'Login exitoso ✅',
            'user': {
                'id': user.id,
                'nombre': user.nombre,
                'username': user.username,
                'email': user.email,
                'rol': user.rol
            }
        })
    antifuerzabruta.registrar_fallo(db_cursor, username, ip)
    return jsonify({'error': 'Credenciales incorrectas ❌'}), 401


# =====================================================
# 2️⃣ LOGOUT
# =====================================================
@bp_auth.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'message': 'Logout exitoso ✅'})


# =====================================================
# 3️⃣ USUARIO LOGUEADO
# =====================================================
@bp_auth.route('/api/user', methods=['GET'])
@login_required
def api_user():
    return jsonify({
        "id": current_user.id,
        "nombre": current_user.nombre,
        "username": current_user.username,
        "email": current_user.email,
        "rol": current_user.rol,
        "duracion_turno": current_user.duracion_turno,
        "foto": current_user.foto
    })


# =====================================================
# 4️⃣ ENVIAR ENLACE DE RECUPERACIÓN
# =====================================================
@bp_auth.route('/api/recover', methods=['POST'])
def api_recover():
    s = get_serializer()
    data = request.json
    email = data.get('email', '').strip().lower()

    if not validar_email(email):
        return jsonify({'error': 'Email inválido'}), 400

    with db_cursor() as (_conn, cursor):
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()

    if not usuario:
        return jsonify({'error': 'No se encontró un usuario con ese email'}), 404

    token = s.dumps(email, salt='reset-password')

    reset_url = f"{current_app.config['FRONTEND_URL']}/reset/{token}"
    msg = Message(f"Recuperación de contraseña - {marca.nombre_corto()}", recipients=[email])
    msg.body = (
        f"Hola {usuario['nombre']},\n\n"
        f"Para restablecer tu contraseña ingresá al siguiente enlace:\n\n"
        f"{reset_url}\n\n"
        f"Este enlace expira en 1 hora."
    )
    mail.send(msg)

    return jsonify({'message': 'Correo enviado para restablecer contraseña ✅'}), 200


# =====================================================
# 5️⃣ RESTABLECER CONTRASEÑA
# =====================================================
@bp_auth.route('/api/reset/<token>', methods=['POST'])
def api_reset_password(token):
    s = get_serializer()

    try:
        email = s.loads(token, salt='reset-password', max_age=3600)
    except SignatureExpired:
        return jsonify({'error': 'El enlace expiró'}), 400
    except BadSignature:
        return jsonify({'error': 'Token inválido'}), 400

    data = request.json or {}
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not new_password or not confirm_password:
        return jsonify({'error': 'Debes completar ambos campos'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400

    #  Validar contraseña fuerte
    if not password_valida(new_password):
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres y contener mayúscula, minúscula, número y símbolo.'}), 400

    #  Hash seguro
    password_hash = generate_password_hash(new_password, method="scrypt")

    with db_cursor(dictionary=False, commit=True) as (_conn, cursor):
        cursor.execute("UPDATE usuarios SET password_hash = %s WHERE email = %s", (password_hash, email))

    return jsonify({'message': 'Contraseña actualizada correctamente ✅'}), 200
