"""Alta autoservicio: de un formulario publico a un consultorio funcionando.

El recorrido tiene tres pasos y una razon para cada uno:

    1. Alguien completa el formulario  -> se guarda la intencion, no se crea nada
    2. Abre el enlace del correo       -> recien ahi se crea la base
    3. Entra a su subdominio

Crear la base en el paso 1 seria mas simple, pero el formulario es publico: un
script podria llenar el servidor de bases vacias. Exigir la casilla de correo no
lo hace imposible, pero lo vuelve caro y deja un rastro.

El aprovisionamiento reutiliza `alta_cliente.crear_cliente()`, el mismo que usa
el script de consola. No puede haber dos caminos de alta que diverjan: si el
autoservicio creara los consultorios de otra manera, un dia se descubriria que
los dados de alta por la web no tienen algo que los otros si.
"""

import re
import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app import plataforma
from app.utils.validacion import password_valida, validar_email

# Cuanto vive un enlace de verificacion sin usar.
HORAS_VALIDEZ = 48

# Dias de prueba que recibe un consultorio nuevo.
DIAS_PRUEBA = 30

# Mismo patron que usa el alta por consola: minusculas, numeros y guiones, sin
# empezar ni terminar con guion. Minimo 3 para no repartir subdominios de una
# o dos letras, que son los mas cotizados.
PATRON_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61})?[a-z0-9]$")
LARGO_MINIMO_SLUG = 3


class ErrorRegistro(Exception):
    """Algo que el usuario puede corregir. El mensaje se le muestra tal cual."""


def validar_slug(slug):
    slug = (slug or "").strip().lower()

    if len(slug) < LARGO_MINIMO_SLUG:
        raise ErrorRegistro(
            f"La direccion debe tener al menos {LARGO_MINIMO_SLUG} caracteres."
        )
    if len(slug) > 63:
        raise ErrorRegistro("La direccion no puede superar los 63 caracteres.")
    if not PATRON_SLUG.match(slug):
        raise ErrorRegistro(
            "La direccion solo admite letras minusculas, numeros y guiones, "
            "y no puede empezar ni terminar con guion."
        )
    if not plataforma.slug_disponible(slug):
        # Mismo mensaje para "ya lo tiene otro" y "esta reservado": la
        # diferencia no le sirve a quien se registra y revela que nombres existen.
        raise ErrorRegistro("Esa direccion no esta disponible.")

    return slug


def _validar_datos(datos):
    nombre = (datos.get("nombre") or "").strip()
    email = (datos.get("email") or "").strip().lower()
    password = datos.get("password") or ""

    if len(nombre) < 3:
        raise ErrorRegistro("El nombre del consultorio es obligatorio.")
    if len(nombre) > 180:
        raise ErrorRegistro("El nombre del consultorio es demasiado largo.")

    if not validar_email(email):
        raise ErrorRegistro("El correo no parece valido.")

    if not password_valida(password):
        raise ErrorRegistro(
            "La contrasena debe tener entre 8 y 64 caracteres, con mayuscula, "
            "minuscula, numero y simbolo."
        )

    return nombre, email, password


def registrar(datos):
    """Guarda la intencion de alta y devuelve el token de verificacion.

    No crea ninguna base: eso pasa cuando se verifica el correo.
    """
    slug = validar_slug(datos.get("slug"))
    nombre, email, password = _validar_datos(datos)

    token = secrets.token_hex(32)
    expira = datetime.now() + timedelta(hours=HORAS_VALIDEZ)

    with plataforma.cursor_plataforma(commit=True) as (_conn, cur):
        # Un registro anterior sin verificar del mismo slug o correo se
        # reemplaza. Sin esto, equivocarse al escribir el correo dejaria el slug
        # bloqueado hasta que caduque, sin forma de reintentar.
        cur.execute(
            "DELETE FROM registros_pendientes "
            "WHERE estado = 'pendiente' AND (slug = %s OR email = %s)",
            (slug, email),
        )
        cur.execute(
            """
            INSERT INTO registros_pendientes
                (slug, nombre, email, password_hash, token, expira_en)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                slug,
                nombre,
                email,
                generate_password_hash(password, method="scrypt"),
                token,
                expira,
            ),
        )

    return token


def buscar_por_token(token):
    if not token:
        return None
    with plataforma.cursor_plataforma() as (_conn, cur):
        cur.execute("SELECT * FROM registros_pendientes WHERE token = %s", (token,))
        return cur.fetchone()


def _marcar(token, estado, error=None, cliente_id=None):
    with plataforma.cursor_plataforma(commit=True) as (_conn, cur):
        cur.execute(
            "UPDATE registros_pendientes "
            "SET estado = %s, error = %s, cliente_id = COALESCE(%s, cliente_id) "
            "WHERE token = %s",
            (estado, error, cliente_id, token),
        )


def verificar_y_crear(token):
    """Confirma el correo y crea el consultorio.

    Devuelve el registro actualizado. La creacion es sincronica porque tarda
    pocos segundos; quien llama decide si la corre en segundo plano.
    """
    registro = buscar_por_token(token)

    if registro is None:
        raise ErrorRegistro("El enlace no es valido.")

    if registro["estado"] == "listo":
        # Reabrir el enlace no tiene que crear un segundo consultorio.
        return registro

    if registro["estado"] == "creando":
        return registro

    if registro["expira_en"] and registro["expira_en"] < datetime.now():
        raise ErrorRegistro("El enlace vencio. Volve a registrarte.")

    # Se comprueba de nuevo: entre el registro y la verificacion pudo pasar un
    # dia, y el slug pudo tomarlo otro que verifico antes.
    if not plataforma.slug_disponible(registro["slug"]):
        raise ErrorRegistro(
            "Mientras tanto alguien tomo esa direccion. Volve a registrarte con otra."
        )

    _marcar(token, "creando")

    try:
        from app import alta_cliente

        resultado = alta_cliente.dar_de_alta(
            slug=registro["slug"],
            nombre=registro["nombre"],
            email=registro["email"],
            dias_prueba=DIAS_PRUEBA,
            password_hash=registro["password_hash"],
        )
    except Exception as exc:  # noqa: BLE001 - se guarda para poder diagnosticar
        _marcar(token, "fallido", error=str(exc)[:500])
        raise

    with plataforma.cursor_plataforma(commit=True) as (_conn, cur):
        cur.execute(
            "UPDATE registros_pendientes "
            "SET estado = 'listo', verificado_en = NOW(), cliente_id = %s, error = NULL "
            "WHERE token = %s",
            (resultado["cliente_id"], token),
        )

    return buscar_por_token(token)


def limpiar_vencidos():
    """Borra los registros que nadie verifico. Lo llama un comando de consola."""
    with plataforma.cursor_plataforma(commit=True) as (_conn, cur):
        cur.execute(
            "DELETE FROM registros_pendientes "
            "WHERE estado = 'pendiente' AND expira_en < NOW()"
        )
        return cur.rowcount
