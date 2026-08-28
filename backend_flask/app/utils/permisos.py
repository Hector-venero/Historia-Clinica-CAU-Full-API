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


def requiere_modulo(nombre_modulo):
    """Restringe una ruta a los consultorios cuyo plan incluye ese modulo.

    El backend valida el plan igual que valida el rol: en el servidor. Que el
    frontend oculte una opcion del menu no es un permiso, es presentacion —
    quien conozca la URL de la API la llama igual.

    En una instalacion de un solo centro no hay plan y todo esta habilitado, asi
    que el decorador no cambia nada.

    Uso:
        @requiere_modulo('recetas')
    """
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app import marca

            if not marca.tiene_modulo(nombre_modulo):
                return jsonify({
                    "error": "El plan contratado no incluye este modulo.",
                    "modulo": nombre_modulo,
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return wrapper
