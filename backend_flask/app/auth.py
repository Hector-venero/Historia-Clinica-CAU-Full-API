from flask_login import UserMixin
from werkzeug.security import check_password_hash

from .database import get_connection

# Campos de perfil que viajan en el usuario de sesion, mas alla de los de
# identidad. El modulo de recetas necesita casi todos: sin matricula ni lugar de
# atencion no se puede emitir.
#
# Estan en una lista y no como parametros sueltos del __init__ porque antes cada
# columna nueva obligaba a tocar tres lugares (la firma, obtener_por_username y
# load_user), y era cuestion de tiempo que uno quedara desactualizado y el campo
# llegara siempre en None.
CAMPOS_PERFIL = (
    "apellido",
    "dni",
    "sexo",
    "telefono",
    "profesion",
    "especialidad",
    "matricula_tipo",
    "matricula_numero",
    "matricula_provincia",
    "lugar_atencion_nombre",
    "lugar_atencion_direccion",
    "lugar_atencion_contacto",
    "lugar_atencion_email",
)


class Usuario(UserMixin):
    def __init__(self, id, nombre, username, email, password_hash, rol,
                 duracion_turno=None, foto=None, **perfil):
        self.id = id
        self.nombre = nombre
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.rol = rol
        self.duracion_turno = duracion_turno
        self.foto = foto
        for campo in CAMPOS_PERFIL:
            setattr(self, campo, perfil.get(campo))

    @classmethod
    def desde_fila(cls, fila):
        """Construye el usuario desde una fila de `usuarios`.

        Es el unico lugar que mapea columnas a atributos: agregar una columna al
        perfil es agregarla a CAMPOS_PERFIL y nada mas.
        """
        if not fila:
            return None
        return cls(
            id=fila["id"],
            nombre=fila["nombre"],
            username=fila["username"],
            email=fila["email"],
            password_hash=fila["password_hash"],
            rol=fila["rol"],
            duracion_turno=fila.get("duracion_turno"),
            foto=fila.get("foto"),
            **{campo: fila.get(campo) for campo in CAMPOS_PERFIL},
        )

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

        return Usuario.desde_fila(data)

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)
