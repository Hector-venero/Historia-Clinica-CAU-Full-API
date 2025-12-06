from flask import Blueprint, request, jsonify, session, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import Usuario
from werkzeug.security import generate_password_hash
import secrets
from app import mail
from flask_mail import Message
from app.database import get_connection
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

bp_auth = Blueprint("auth", __name__)

# 🔹 Función auxiliar para crear el serializador cuando Flask ya está listo
def get_serializer():
    return URLSafeTimedSerializer(current_app.secret_key)

# =====================================================
# 1️⃣ Login
# =====================================================
@bp_auth.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = Usuario.obtener_por_username(username)

    if user and user.verificar_password(password):
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
    return jsonify({'error': 'Credenciales incorrectas ❌'}), 401


# =====================================================
# 2️⃣ Logout
# =====================================================
@bp_auth.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'message': 'Logout exitoso ✅'})


# =====================================================
# 3️⃣ Usuario logueado
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
# 4️⃣ Enviar enlace de recuperación
# =====================================================
@bp_auth.route('/api/recover', methods=['POST'])
def api_recover():
    s = get_serializer()  # ✅ se genera dentro del contexto
    data = request.json
    email = data.get('email', '').strip().lower()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    usuario = cursor.fetchone()
    conn.close()

    if not usuario:
        return jsonify({'error': 'No se encontró un usuario con ese email'}), 404

    # Generar token válido por 1 hora
    token = s.dumps(email, salt='reset-password')

    reset_url = f"http://localhost:5173/reset/{token}"
    msg = Message("Recuperación de contraseña - Historia Clínica CAU", recipients=[email])
    msg.body = (
        f"Hola {usuario['nombre']},\n\n"
        f"Recibimos una solicitud para restablecer tu contraseña.\n"
        f"Para continuar, hacé clic en el siguiente enlace:\n\n"
        f"{reset_url}\n\n"
        f"Este enlace expirará en 1 hora.\n\n"
        f"Si no realizaste esta solicitud, podés ignorar este mensaje.\n\n"
        f"Gracias,\nSistema de Historias Clínicas del CAU"
    )
    mail.send(msg)

    return jsonify({'message': 'Se envió un correo con el enlace para restablecer tu contraseña ✅'}), 200


# =====================================================
# 5️⃣ Restablecer contraseña
# =====================================================
@bp_auth.route('/api/reset/<token>', methods=['POST'])
def api_reset_password(token):
    s = get_serializer()  # ✅ también aquí dentro
    try:
        # Verificar token (expira a la hora)
        email = s.loads(token, salt='reset-password', max_age=3600)
    except SignatureExpired:
        return jsonify({'error': 'El enlace expiró. Solicitá uno nuevo.'}), 400
    except BadSignature:
        return jsonify({'error': 'Token inválido.'}), 400

    data = request.json
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not new_password or not confirm_password:
        return jsonify({'error': 'Debes ingresar y confirmar la contraseña'}), 400
    if new_password != confirm_password:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400

    password_hash = generate_password_hash(new_password)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET password_hash = %s WHERE email = %s", (password_hash, email))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Contraseña actualizada correctamente ✅'}), 200
