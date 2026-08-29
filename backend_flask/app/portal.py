"""Plano del paciente: su cuenta y el buzon de lo que le enviaron.

Es la unica parte del sistema que habla con la base `portal`, igual que
`plataforma.py` es la unica que habla con el plano de control. No usa
`database.get_connection()` a proposito: esa resuelve la base **del consultorio
actual**, y mezclarlas seria el camino corto a que un pedido del portal termine
leyendo una base clinica.

**Aca no vive la historia clinica.** Vive lo que un profesional decidio enviarle
al paciente. La distincion es la que hace que este plano pueda ser una sola base
compartida sin romper el aislamiento entre consultorios: nadie publica nada que
no haya decidido publicar.
"""

import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta

import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash

from app.utils.validacion import password_valida, validar_email

# Tipos de documento que se aceptan como identidad.
TIPOS_DOCUMENTO = ("DNI", "CI", "LC", "LE", "PASAPORTE")

# Que puede mandarle un profesional a un paciente.
TIPOS_DOCUMENTO_CLINICO = ("estudio", "receta", "informe", "indicacion")

HORAS_VALIDEZ_REGISTRO = 48


class ErrorPortal(Exception):
    """Algo que el usuario puede corregir. El mensaje se le muestra tal cual."""


def _config():
    # `or` y no un default de os.getenv: docker compose pasa las variables no
    # definidas como cadena vacia. Ver la nota en migrate.py.
    return {
        "host": os.getenv("PORTAL_DB_HOST") or os.getenv("DB_HOST") or "db",
        "port": int(os.getenv("PORTAL_DB_PORT") or os.getenv("DB_PORT") or "3306"),
        "user": os.getenv("PORTAL_DB_USER") or "root",
        "password": os.getenv("PORTAL_DB_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD") or "",
        "database": os.getenv("PORTAL_DB_NAME") or "portal",
    }


@contextmanager
def cursor_portal(commit=False):
    """Mismo contrato que `database.db_cursor()`, contra el plano del paciente."""
    conn = mysql.connector.connect(**_config())
    cur = conn.cursor(dictionary=True)
    try:
        yield conn, cur
        if commit:
            conn.commit()
    except Exception:
        if commit:
            try:
                conn.rollback()
            except mysql.connector.Error:
                pass
        raise
    finally:
        try:
            cur.close()
        except mysql.connector.Error:
            pass
        conn.close()


# --------------------------------------------------------------- identidad


def normalizar_documento(tipo, numero):
    """Deja el documento en la forma canonica con la que se compara.

    Sin esto, "30.111.222" y "30111222" serian dos personas distintas, y un
    estudio enviado con puntos no le llegaria nunca a quien se registro sin
    ellos. Se quitan puntos, espacios y guiones.
    """
    tipo = (tipo or "DNI").strip().upper()
    if tipo not in TIPOS_DOCUMENTO:
        raise ErrorPortal("Tipo de documento no valido.")

    numero = "".join(c for c in (numero or "") if c.isalnum()).upper()
    if not numero:
        raise ErrorPortal("El numero de documento es obligatorio.")
    if len(numero) > 30:
        raise ErrorPortal("El numero de documento es demasiado largo.")

    return tipo, numero


class Paciente:
    """La cuenta de un paciente, tal como la usa Flask-Login.

    El identificador que viaja en la sesion lleva el prefijo `p:` para que el
    cargador de usuario sepa que es un paciente y no un miembro del personal de
    un consultorio: son entidades distintas, en bases distintas, y el numero 1
    existe en las dos.
    """

    def __init__(self, fila):
        self.id = fila["id"]
        self.tipo_documento = fila["tipo_documento"]
        self.numero_documento = fila["numero_documento"]
        self.nombre = fila["nombre"]
        self.apellido = fila["apellido"]
        self.email = fila["email"]
        self.telefono = fila.get("telefono")
        self.fecha_nacimiento = fila.get("fecha_nacimiento")
        self.cobertura = fila.get("cobertura")
        self.plan_cobertura = fila.get("plan_cobertura")
        self.nro_afiliado = fila.get("nro_afiliado")
        self.activo = bool(fila.get("activo", 1))

    # --- lo que Flask-Login necesita ---
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.activo

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return f"p:{self.id}"

    # --- para distinguirlo del personal en las rutas ---
    @property
    def es_paciente(self):
        return True

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}".strip()

    def a_json(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "email": self.email,
            "telefono": self.telefono,
            "tipo_documento": self.tipo_documento,
            "numero_documento": self.numero_documento,
            "cobertura": self.cobertura,
            "plan_cobertura": self.plan_cobertura,
            "nro_afiliado": self.nro_afiliado,
        }

    def __repr__(self):
        return f"<Paciente {self.tipo_documento} {self.numero_documento}>"


def buscar_por_id(cuenta_id):
    with cursor_portal() as (_conn, cur):
        cur.execute(
            "SELECT * FROM pacientes_cuenta WHERE id = %s AND activo = 1",
            (cuenta_id,),
        )
        fila = cur.fetchone()
    return Paciente(fila) if fila else None


def buscar_por_email(email):
    with cursor_portal() as (_conn, cur):
        cur.execute(
            "SELECT * FROM pacientes_cuenta WHERE email = %s AND activo = 1",
            ((email or "").strip().lower(),),
        )
        return cur.fetchone()


def buscar_por_documento(tipo, numero):
    tipo, numero = normalizar_documento(tipo, numero)
    with cursor_portal() as (_conn, cur):
        cur.execute(
            "SELECT * FROM pacientes_cuenta "
            "WHERE tipo_documento = %s AND numero_documento = %s AND activo = 1",
            (tipo, numero),
        )
        fila = cur.fetchone()
    return Paciente(fila) if fila else None


def autenticar(email, password):
    """Devuelve el Paciente si las credenciales son validas, o None.

    Mismo mensaje para "no existe" y "clave incorrecta": distinguirlos deja
    averiguar que correos estan registrados.
    """
    fila = buscar_por_email(email)
    if not fila:
        return None
    if not check_password_hash(fila["password_hash"], password or ""):
        return None

    with cursor_portal(commit=True) as (_conn, cur):
        cur.execute(
            "UPDATE pacientes_cuenta SET ultimo_acceso = NOW() WHERE id = %s",
            (fila["id"],),
        )

    return Paciente(fila)


# ----------------------------------------------------------------- registro


def _validar_alta(datos):
    tipo, numero = normalizar_documento(
        datos.get("tipo_documento"), datos.get("numero_documento")
    )

    nombre = (datos.get("nombre") or "").strip()
    apellido = (datos.get("apellido") or "").strip()
    email = (datos.get("email") or "").strip().lower()
    password = datos.get("password") or ""

    if not nombre or not apellido:
        raise ErrorPortal("El nombre y el apellido son obligatorios.")
    if not validar_email(email):
        raise ErrorPortal("El correo no parece valido.")
    if not password_valida(password):
        raise ErrorPortal(
            "La contrasena debe tener entre 8 y 64 caracteres, con mayuscula, "
            "minuscula, numero y simbolo."
        )

    return tipo, numero, nombre, apellido, email, password


def registrar(datos):
    """Guarda la intencion de alta y devuelve el token de verificacion.

    No crea la cuenta: eso pasa cuando se verifica el correo. Mismo criterio que
    el registro de consultorios — el formulario es publico.
    """
    tipo, numero, nombre, apellido, email, password = _validar_alta(datos)

    with cursor_portal() as (_conn, cur):
        cur.execute(
            "SELECT 1 FROM pacientes_cuenta "
            "WHERE (tipo_documento = %s AND numero_documento = %s) OR email = %s",
            (tipo, numero, email),
        )
        if cur.fetchone():
            # No se dice cual de los dos: saber que un documento ya tiene cuenta
            # es informacion sobre una persona.
            raise ErrorPortal(
                "Ya existe una cuenta con esos datos. Proba iniciar sesion o "
                "recuperar tu contrasena."
            )

    token = secrets.token_hex(32)
    expira = datetime.now() + timedelta(hours=HORAS_VALIDEZ_REGISTRO)

    with cursor_portal(commit=True) as (_conn, cur):
        # Un intento anterior sin verificar se reemplaza: equivocarse al escribir
        # el correo no puede dejar el documento bloqueado hasta que caduque.
        cur.execute(
            "DELETE FROM registros_paciente "
            "WHERE estado = 'pendiente' AND ("
            "  (tipo_documento = %s AND numero_documento = %s) OR email = %s)",
            (tipo, numero, email),
        )
        cur.execute(
            """
            INSERT INTO registros_paciente
                (tipo_documento, numero_documento, nombre, apellido, email,
                 password_hash, telefono, fecha_nacimiento, token, expira_en)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tipo, numero, nombre, apellido, email,
                generate_password_hash(password, method="scrypt"),
                (datos.get("telefono") or "").strip() or None,
                datos.get("fecha_nacimiento") or None,
                token, expira,
            ),
        )

    return token


def verificar_registro(token):
    """Confirma el correo y crea la cuenta. Devuelve el Paciente."""
    with cursor_portal() as (_conn, cur):
        cur.execute("SELECT * FROM registros_paciente WHERE token = %s", (token,))
        registro = cur.fetchone()

    if registro is None:
        raise ErrorPortal("El enlace no es valido.")

    if registro["estado"] == "listo":
        # Reabrir el enlace no crea una segunda cuenta.
        return buscar_por_documento(
            registro["tipo_documento"], registro["numero_documento"]
        )

    if registro["expira_en"] and registro["expira_en"] < datetime.now():
        raise ErrorPortal("El enlace vencio. Volve a registrarte.")

    with cursor_portal(commit=True) as (_conn, cur):
        cur.execute(
            """
            INSERT INTO pacientes_cuenta
                (tipo_documento, numero_documento, nombre, apellido, email,
                 password_hash, telefono, fecha_nacimiento)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                registro["tipo_documento"], registro["numero_documento"],
                registro["nombre"], registro["apellido"], registro["email"],
                registro["password_hash"], registro["telefono"],
                registro["fecha_nacimiento"],
            ),
        )
        cur.execute(
            "UPDATE registros_paciente SET estado = 'listo', verificado_en = NOW() "
            "WHERE token = %s",
            (token,),
        )

    return buscar_por_documento(
        registro["tipo_documento"], registro["numero_documento"]
    )


def cambiar_password(cuenta_id, password):
    """Fija una contrasena nueva. La valida antes: es la puerta a datos de salud."""
    if not password_valida(password):
        raise ErrorPortal(
            "La contrasena debe tener entre 8 y 64 caracteres, con mayuscula, "
            "minuscula, numero y simbolo."
        )

    with cursor_portal(commit=True) as (_conn, cur):
        cur.execute(
            "UPDATE pacientes_cuenta SET password_hash = %s WHERE id = %s",
            (generate_password_hash(password, method="scrypt"), cuenta_id),
        )
        return cur.rowcount


def actualizar_perfil(cuenta_id, datos):
    """Los datos que el paciente puede cambiar de si mismo.

    El documento NO esta: es su identidad, y cambiarlo lo desconectaria de todo
    lo que le enviaron. Si esta mal cargado, lo corrige soporte.
    """
    campos = {
        "telefono": (datos.get("telefono") or "").strip() or None,
        "cobertura": (datos.get("cobertura") or "").strip() or None,
        "plan_cobertura": (datos.get("plan_cobertura") or "").strip() or None,
        "nro_afiliado": (datos.get("nro_afiliado") or "").strip() or None,
    }
    asignaciones = ", ".join(f"{c} = %s" for c in campos)

    with cursor_portal(commit=True) as (_conn, cur):
        cur.execute(
            f"UPDATE pacientes_cuenta SET {asignaciones} WHERE id = %s",
            (*campos.values(), cuenta_id),
        )

    return buscar_por_id(cuenta_id)


# ------------------------------------------------------------------- buzon


def documentos_de(tipo, numero):
    """Lo que le enviaron a esa persona, lo mas reciente primero."""
    tipo, numero = normalizar_documento(tipo, numero)
    with cursor_portal() as (_conn, cur):
        cur.execute(
            "SELECT * FROM documentos "
            "WHERE tipo_documento = %s AND numero_documento = %s "
            "ORDER BY enviado_en DESC",
            (tipo, numero),
        )
        return cur.fetchall()


def documento_de(documento_id, tipo, numero):
    """Un documento, **solo si es de esa persona**.

    El dueño va en el WHERE y no se comprueba despues de leerlo: asi no hay forma
    de escribir la comprobacion al reves por accidente.
    """
    tipo, numero = normalizar_documento(tipo, numero)
    with cursor_portal() as (_conn, cur):
        cur.execute(
            "SELECT * FROM documentos "
            "WHERE id = %s AND tipo_documento = %s AND numero_documento = %s",
            (documento_id, tipo, numero),
        )
        return cur.fetchone()


def marcar_leido(documento_id, tipo, numero):
    tipo, numero = normalizar_documento(tipo, numero)
    with cursor_portal(commit=True) as (_conn, cur):
        cur.execute(
            "UPDATE documentos SET leido_en = NOW() "
            "WHERE id = %s AND tipo_documento = %s AND numero_documento = %s "
            "AND leido_en IS NULL",
            (documento_id, tipo, numero),
        )
        return cur.rowcount


def sin_leer(tipo, numero):
    tipo, numero = normalizar_documento(tipo, numero)
    with cursor_portal() as (_conn, cur):
        cur.execute(
            "SELECT COUNT(*) AS n FROM documentos "
            "WHERE tipo_documento = %s AND numero_documento = %s AND leido_en IS NULL",
            (tipo, numero),
        )
        return cur.fetchone()["n"]


def guardar_documento(*, tipo_documento, numero_documento, consultorio_slug,
                      consultorio_nombre, profesional_nombre, tipo, titulo,
                      descripcion=None, archivo_token=None, archivo_nombre=None):
    """Registra un envio en el buzon del paciente.

    Lo llama el consultorio al pulsar "Enviar al paciente". Si esa persona
    todavia no tiene cuenta, el documento queda igual y aparece cuando se
    registra: por eso se guarda contra el documento y no contra una cuenta.
    """
    tipo_doc, numero = normalizar_documento(tipo_documento, numero_documento)

    if tipo not in TIPOS_DOCUMENTO_CLINICO:
        raise ErrorPortal(f"Tipo de documento clinico no valido: {tipo}")
    if not (titulo or "").strip():
        raise ErrorPortal("El documento necesita un titulo.")

    with cursor_portal(commit=True) as (_conn, cur):
        cur.execute(
            """
            INSERT INTO documentos
                (tipo_documento, numero_documento, consultorio_slug,
                 consultorio_nombre, profesional_nombre, tipo, titulo,
                 descripcion, archivo_token, archivo_nombre)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (tipo_doc, numero, consultorio_slug, consultorio_nombre,
             profesional_nombre, tipo, titulo.strip(), descripcion,
             archivo_token, archivo_nombre),
        )
        return cur.lastrowid


def nuevo_token_archivo():
    """Nombre de carpeta para un adjunto del portal.

    Aleatorio y sin relacion con el documento del paciente: la ruta de un archivo
    no puede permitir averiguar de quien es.
    """
    return secrets.token_hex(16)
