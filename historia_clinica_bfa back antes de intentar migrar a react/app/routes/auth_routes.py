from flask import Blueprint, request, jsonify, session, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import Usuario
from werkzeug.security import generate_password_hash
import secrets
from app import mail
from flask_mail import Message
from app.database import get_connection

bp_auth = Blueprint("auth", __name__)

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

@bp_auth.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'message': 'Logout exitoso ✅'})

@bp_auth.route('/api/user', methods=['GET'])
@login_required
def api_user():
    return jsonify({
        "id": current_user.id,
        "nombre": current_user.nombre,
        "username": current_user.username,
        "email": current_user.email,
        "rol": current_user.rol
    })

@bp_auth.route('/api/recover', methods=['POST'])
def api_recover():
    data = request.json
    email = data.get('email').strip().lower()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    usuario = cursor.fetchone()
    conn.close()

    if usuario:
        token = secrets.token_urlsafe(32)
        session['reset_token'] = token
        session['reset_user'] = usuario['username']
        reset_url = url_for('api_reset_password', token=token, _external=True)

        msg = Message("Recuperación de contraseña", recipients=[email])
        msg.body = (
            f"Hola,\n\n"
            f"Recibimos una solicitud para restablecer la contraseña del usuario asociado al correo {email}.\n\n"
            f"Si fuiste vos, hacé clic en el siguiente enlace:\n\n"
            f"{reset_url}\n\n"
            f"Si no realizaste esta solicitud, podés ignorar este mensaje.\n\n"
            f"Gracias,\nSistema HC"
        )
        mail.send(msg)

        return jsonify({'message': 'Email enviado con enlace para restablecer contraseña ✅'})
    else:
        return jsonify({'error': 'No se encontró un usuario con ese email'}), 404

@bp_auth.route('/api/reset/<token>', methods=['POST'])
def api_reset_password(token):
    if session.get('reset_token') != token:
        return jsonify({'error': 'Token inválido o expirado'}), 403

    data = request.json
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if new_password != confirm_password:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400

    username = session['reset_user']
    conn = get_connection()
    cursor = conn.cursor()
    hash_pw = generate_password_hash(new_password)
    cursor.execute("UPDATE usuarios SET password_hash = %s WHERE username = %s", (hash_pw, username))
    conn.commit()
    conn.close()

    session.pop('reset_token', None)
    session.pop('reset_user', None)

    return jsonify({'message': 'Contraseña actualizada correctamente ✅'})