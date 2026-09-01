"""Servicios (prestaciones) del consultorio.

Un turno hasta ahora era una franja de tiempo con un `motivo` de texto libre, y
todos los turnos de un profesional duraban lo mismo. Con servicios cada turno es
*de algo*, con su duracion y su precio: una primera consulta de 40 minutos y un
control de 15 dejan de tener que durar igual.

**Es opcional, y esa es la decision que ordena todo el modulo.** Un consultorio
que no cargue ningun servicio funciona exactamente como antes: la duracion sigue
saliendo de `usuarios.duracion_turno`. Es lo que permite soltar esto sin migrar
a nadie ni obligar a nadie a configurar algo antes de poder agendar.

Un servicio con `usuario_id` NULL es de todo el consultorio; con valor, es de ese
profesional. Ver la migracion `20260901_servicios.sql` por que no hay tabla de
union.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.database import db_cursor
from app.utils.permisos import requiere_rol

bp_servicios = Blueprint("servicios", __name__)

# Quien puede tocar el catalogo. Un `profesional` administra los suyos; la
# direccion y el administrativo, los del consultorio.
ROLES_ESCRITURA = ("director", "administrativo", "profesional")

DURACION_MINIMA = 5
DURACION_MAXIMA = 480  # ocho horas: mas que eso no es un turno


def _limpiar(valor, largo):
    return (str(valor).strip()[:largo]) if valor is not None else None


def _leer_datos(data):
    """Valida el cuerpo. Devuelve (campos, error)."""
    nombre = _limpiar(data.get("nombre"), 120)
    if not nombre:
        return None, "El nombre es obligatorio"

    try:
        duracion = int(data.get("duracion_minutos"))
    except (TypeError, ValueError):
        return None, "La duracion tiene que ser un numero de minutos"
    if not (DURACION_MINIMA <= duracion <= DURACION_MAXIMA):
        return None, f"La duracion tiene que estar entre {DURACION_MINIMA} y {DURACION_MAXIMA} minutos"

    # El precio es opcional a proposito: muchos consultorios no quieren tenerlo
    # cargado en el sistema, y obligarlo los dejaria afuera de los servicios.
    precio = data.get("precio")
    if precio in ("", None):
        precio = None
    else:
        try:
            precio = round(float(precio), 2)
        except (TypeError, ValueError):
            return None, "El precio tiene que ser un numero"
        if precio < 0:
            return None, "El precio no puede ser negativo"

    return {
        "nombre": nombre,
        "descripcion": _limpiar(data.get("descripcion"), 255),
        "duracion_minutos": duracion,
        "precio": precio,
        "activo": 1 if data.get("activo", True) else 0,
    }, None


def _usuario_destino(data):
    """De quien es el servicio que se esta creando o editando.

    Un `profesional` solo puede tocar los suyos: si mandara el id de otro estaria
    cambiandole la agenda a un colega. La direccion y el administrativo pueden
    dejarlo en NULL, que significa "de todo el consultorio".
    """
    if current_user.rol == "profesional":
        return current_user.id, None

    crudo = data.get("usuario_id")
    if crudo in ("", None):
        return None, None
    try:
        return int(crudo), None
    except (TypeError, ValueError):
        return None, "usuario_id invalido"


def _puede_tocar(fila):
    """Un profesional solo administra sus propios servicios."""
    if current_user.rol != "profesional":
        return True
    return fila.get("usuario_id") == current_user.id


def _serializar(fila):
    return {
        "id": fila["id"],
        "usuario_id": fila["usuario_id"],
        "profesional": fila.get("profesional"),
        "nombre": fila["nombre"],
        "descripcion": fila["descripcion"],
        "duracion_minutos": fila["duracion_minutos"],
        # DECIMAL vuelve como Decimal, que jsonify no serializa.
        "precio": float(fila["precio"]) if fila["precio"] is not None else None,
        "activo": bool(fila["activo"]),
    }


@bp_servicios.get("/api/servicios")
@login_required
def listar():
    """El catalogo.

    Con `?usuario_id=` devuelve los que ese profesional puede dar: los suyos y
    los del consultorio. Es la consulta que necesitan las pantallas que agendan.
    Sin parametro, el catalogo entero, que es lo que necesita la de configurar.

    `?activos=1` deja afuera los dados de baja: al agendar no se ofrece un
    servicio que se discontinuo, pero al configurarlo hay que poder verlo.
    """
    usuario_id = request.args.get("usuario_id", type=int)
    solo_activos = request.args.get("activos") in ("1", "true", "si")

    condiciones = []
    parametros = []
    if usuario_id:
        condiciones.append("(s.usuario_id IS NULL OR s.usuario_id = %s)")
        parametros.append(usuario_id)
    if solo_activos:
        condiciones.append("s.activo = 1")
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    with db_cursor() as (_conn, cursor):
        cursor.execute(
            f"""
            SELECT s.id, s.usuario_id, s.nombre, s.descripcion, s.duracion_minutos,
                   s.precio, s.activo,
                   TRIM(CONCAT(u.nombre, ' ', COALESCE(u.apellido, ''))) AS profesional
            FROM servicios s
            LEFT JOIN usuarios u ON u.id = s.usuario_id
            {where}
            ORDER BY s.activo DESC, s.nombre
            """,
            tuple(parametros),
        )
        return jsonify([_serializar(f) for f in cursor.fetchall()])


@bp_servicios.post("/api/servicios")
@login_required
@requiere_rol(*ROLES_ESCRITURA)
def crear():
    data = request.get_json(silent=True) or {}
    campos, error = _leer_datos(data)
    if error:
        return jsonify({"error": error}), 400

    destino, error = _usuario_destino(data)
    if error:
        return jsonify({"error": error}), 400

    with db_cursor(commit=True) as (_conn, cursor):
        cursor.execute(
            """
            INSERT INTO servicios (usuario_id, nombre, descripcion, duracion_minutos, precio, activo)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                destino,
                campos["nombre"],
                campos["descripcion"],
                campos["duracion_minutos"],
                campos["precio"],
                campos["activo"],
            ),
        )
        nuevo_id = cursor.lastrowid

    return jsonify({"id": nuevo_id, "message": "Servicio creado"}), 201


@bp_servicios.put("/api/servicios/<int:servicio_id>")
@login_required
@requiere_rol(*ROLES_ESCRITURA)
def editar(servicio_id):
    data = request.get_json(silent=True) or {}
    campos, error = _leer_datos(data)
    if error:
        return jsonify({"error": error}), 400

    with db_cursor(commit=True) as (_conn, cursor):
        cursor.execute("SELECT id, usuario_id FROM servicios WHERE id = %s", (servicio_id,))
        fila = cursor.fetchone()
        if not fila:
            return jsonify({"error": "Servicio no encontrado"}), 404
        if not _puede_tocar(fila):
            return jsonify({"error": "No autorizado"}), 403

        cursor.execute(
            """
            UPDATE servicios
            SET nombre=%s, descripcion=%s, duracion_minutos=%s, precio=%s, activo=%s
            WHERE id=%s
            """,
            (
                campos["nombre"],
                campos["descripcion"],
                campos["duracion_minutos"],
                campos["precio"],
                campos["activo"],
                servicio_id,
            ),
        )

    return jsonify({"message": "Servicio actualizado"})


@bp_servicios.delete("/api/servicios/<int:servicio_id>")
@login_required
@requiere_rol(*ROLES_ESCRITURA)
def borrar(servicio_id):
    """Da de baja el servicio; no lo borra.

    Es baja logica y no DELETE porque los turnos ya dados apuntan al servicio, y
    un consultorio que discontinua una prestacion sigue queriendo ver con que se
    atendio el mes pasado. La baja lo saca de donde se elige, que es lo que se
    quiere.
    """
    with db_cursor(commit=True) as (_conn, cursor):
        cursor.execute("SELECT id, usuario_id FROM servicios WHERE id = %s", (servicio_id,))
        fila = cursor.fetchone()
        if not fila:
            return jsonify({"error": "Servicio no encontrado"}), 404
        if not _puede_tocar(fila):
            return jsonify({"error": "No autorizado"}), 403

        cursor.execute("UPDATE servicios SET activo = 0 WHERE id = %s", (servicio_id,))

    return jsonify({"message": "Servicio dado de baja"})
