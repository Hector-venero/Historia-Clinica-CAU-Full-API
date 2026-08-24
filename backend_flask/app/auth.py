from flask_login import UserMixin
from werkzeug.security import check_password_hash
from .database import get_connection

class Usuario(UserMixin):
    def __init__(self, id, nombre, username, email, password_hash, rol, duracion_turno,
                 foto=None, apellido=None, dni=None, sexo=None, profesion=None,
                 matricula_tipo=None, matricula_numero=None, matricula_provincia=None):
        self.id = id
        self.nombre = nombre
        self.apellido = apellido
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.rol = rol
        self.duracion_turno = duracion_turno
        self.foto = foto
        self.dni = dni
        self.sexo = sexo
        self.profesion = profesion
        self.matricula_tipo = matricula_tipo
        self.matricula_numero = matricula_numero
        self.matricula_provincia = matricula_provincia

    @staticmethod
    def obtener_por_username(username):
        conn = get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # activo = 1 es parte del criterio de autenticacion, no un filtro de
            # presentacion: sin el, un usuario dado de baja seguia pudiendo loguearse
            # (los usuarios se borran con soft-delete, nunca se eliminan de la tabla).
            cursor.execute(
                "SELECT * FROM usuarios WHERE username = %s AND activo = 1",
                (username,),
            )
            data = cursor.fetchone()
        finally:
            conn.close()

        if data:
            return Usuario(
                id=data['id'],
                nombre=data['nombre'],
                username=data['username'],
                email=data['email'],
                password_hash=data['password_hash'],
                rol=data['rol'],
                duracion_turno=data.get('duracion_turno'),
                foto=data.get('foto'),
                apellido=data.get('apellido'),
                dni=data.get('dni'),
                sexo=data.get('sexo'),
                profesion=data.get('profesion'),
                matricula_tipo=data.get('matricula_tipo'),
                matricula_numero=data.get('matricula_numero'),
                matricula_provincia=data.get('matricula_provincia'),
            )
        return None

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)
