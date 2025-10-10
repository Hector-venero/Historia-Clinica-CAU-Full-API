from flask_login import UserMixin
from werkzeug.security import check_password_hash
from .database import get_connection

class Usuario(UserMixin):
    def __init__(self, id, nombre, username, email, password_hash, rol):
        self.id = id
        self.nombre = nombre
        self.username = username
        self.email = email       # ✅ ahora lo guardamos
        self.password_hash = password_hash
        self.rol = rol  

    @staticmethod
    def obtener_por_username(username):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
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

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)
