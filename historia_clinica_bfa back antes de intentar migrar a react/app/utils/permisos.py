from functools import wraps
from flask import jsonify
from flask_login import current_user

def requiere_rol(*roles_permitidos):
    """
    Decorador para restringir acceso a ciertos roles.
    Uso:
        @requiere_rol('director')
        @requiere_rol('director', 'profesional')
    """
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Si no está autenticado
            if not current_user.is_authenticated:
                return jsonify({"error": "No autorizado"}), 401

            # Si no tiene un rol permitido
            if current_user.rol not in roles_permitidos:
                return jsonify({"error": "Acceso denegado"}), 403

            return f(*args, **kwargs)
        return decorated_function
    return wrapper
