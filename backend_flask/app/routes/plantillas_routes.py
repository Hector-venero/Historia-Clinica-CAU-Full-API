"""Plantillas de texto clinico.

Buena parte de lo que se escribe en una evolucion se repite: el control de una
misma patologia, las indicaciones post quirurgicas, la pauta de alarma que hay
que dejar por escrito siempre. Hoy se vuelve a tipear cada vez, y lo que se
tipea de nuevo sale distinto cada vez — que en una historia clinica no es solo
una perdida de tiempo.

Mismo modelo que `servicios`: `usuario_id` NULL es del consultorio, con valor es
de ese profesional, y un profesional solo administra los suyos.

⚠️ La plantilla es un **punto de partida**, no el texto final: se inserta en el
formulario y se edita antes de guardar. Nunca se escribe sola en una evolucion.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.database import db_cursor
from app.utils.permisos import requiere_rol

bp_plantillas = Blueprint("plantillas", __name__)

# Quien escribe en la historia clinica. Un administrativo no redacta evoluciones,
# asi que tampoco define las plantillas con las que se redactan.
ROLES_ESCRITURA = ("director", "profesional")

# Los campos del formulario que aceptan plantilla. Separarlas evita tener que
# leer veinte opciones para encontrar una: un texto de indicaciones no sirve
# como evolucion.
CAMPOS = ("evolucion", "indicaciones")

LARGO_MAXIMO = 5000


def _puede_tocar(fila):
    if current_user.rol != "profesional":
        return True
    return fila.get("usuario_id") == current_user.id


def _leer_datos(data):
    nombre = (data.get("nombre") or "").strip()[:120]
    if not nombre:
        return None, "El nombre es obligatorio"

    cuerpo = (data.get("cuerpo") or "").strip()
    if not cuerpo:
        return None, "La plantilla no puede estar vacia"
    if len(cuerpo) > LARGO_MAXIMO:
        return None, f"La plantilla no puede superar los {LARGO_MAXIMO} caracteres"

    campo = (data.get("campo") or "evolucion").strip()
    if campo not in CAMPOS:
        return None, f"Campo invalido. Los validos son: {', '.join(CAMPOS)}"

    return {
        "nombre": nombre,
        "cuerpo": cuerpo,
        "campo": campo,
        "activo": 1 if data.get("activo", True) else 0,
    }, None


def _usuario_destino(data):
    """De quien es. Un profesional solo crea las suyas."""
    if current_user.rol == "profesional":
        return current_user.id, None
    crudo = data.get("usuario_id")
    if crudo in ("", None):
        return None, None
    try:
        return int(crudo), None
    except (TypeError, ValueError):
        return None, "usuario_id invalido"


def _serializar(fila):
    return {
        "id": fila["id"],
        "usuario_id": fila["usuario_id"],
        "campo": fila["campo"],
        "nombre": fila["nombre"],
        "cuerpo": fila["cuerpo"],
        "activo": bool(fila["activo"]),
    }


@bp_plantillas.get("/api/plantillas")
@login_required
def listar():
    """Las plantillas que puede usar quien pregunta.

    Por defecto, las suyas y las del consultorio, solo activas: es la consulta
    que hace la pantalla de escribir una evolucion.

    `?todas=1` devuelve el catalogo completo, para la pantalla de administrarlas.
    """
    campo = request.args.get("campo")
    todas = request.args.get("todas") in ("1", "true", "si")

    condiciones = []
    parametros = []
    if campo:
        condiciones.append("p.campo = %s")
        parametros.append(campo)
    if not todas:
        condiciones.append("p.activo = 1")
        condiciones.append("(p.usuario_id IS NULL OR p.usuario_id = %s)")
        parametros.append(current_user.id)
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    with db_cursor() as (_conn, cursor):
        cursor.execute(
            f"""
            SELECT p.id, p.usuario_id, p.campo, p.nombre, p.cuerpo, p.activo
            FROM plantillas_texto p
            {where}
            ORDER BY p.campo, p.nombre
            """,
            tuple(parametros),
        )
        return jsonify([_serializar(f) for f in cursor.fetchall()])


@bp_plantillas.post("/api/plantillas")
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
            INSERT INTO plantillas_texto (usuario_id, campo, nombre, cuerpo, activo)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (destino, campos["campo"], campos["nombre"], campos["cuerpo"], campos["activo"]),
        )
        nueva = cursor.lastrowid

    return jsonify({"id": nueva, "message": "Plantilla creada"}), 201


@bp_plantillas.put("/api/plantillas/<int:plantilla_id>")
@login_required
@requiere_rol(*ROLES_ESCRITURA)
def editar(plantilla_id):
    data = request.get_json(silent=True) or {}
    campos, error = _leer_datos(data)
    if error:
        return jsonify({"error": error}), 400

    with db_cursor(commit=True) as (_conn, cursor):
        cursor.execute(
            "SELECT id, usuario_id FROM plantillas_texto WHERE id = %s", (plantilla_id,)
        )
        fila = cursor.fetchone()
        if not fila:
            return jsonify({"error": "Plantilla no encontrada"}), 404
        if not _puede_tocar(fila):
            return jsonify({"error": "No autorizado"}), 403

        cursor.execute(
            """
            UPDATE plantillas_texto
            SET campo=%s, nombre=%s, cuerpo=%s, activo=%s
            WHERE id=%s
            """,
            (campos["campo"], campos["nombre"], campos["cuerpo"], campos["activo"], plantilla_id),
        )

    return jsonify({"message": "Plantilla actualizada"})


@bp_plantillas.delete("/api/plantillas/<int:plantilla_id>")
@login_required
@requiere_rol(*ROLES_ESCRITURA)
def borrar(plantilla_id):
    """Aca si se borra de verdad.

    A diferencia de `servicios`, una plantilla no queda referenciada por nada: su
    texto se copia al formulario y lo que se guarda en la evolucion es el texto,
    no un puntero. Borrarla no puede dejar huerfano a ningun registro clinico.
    """
    with db_cursor(commit=True) as (_conn, cursor):
        cursor.execute(
            "SELECT id, usuario_id FROM plantillas_texto WHERE id = %s", (plantilla_id,)
        )
        fila = cursor.fetchone()
        if not fila:
            return jsonify({"error": "Plantilla no encontrada"}), 404
        if not _puede_tocar(fila):
            return jsonify({"error": "No autorizado"}), 403

        cursor.execute("DELETE FROM plantillas_texto WHERE id = %s", (plantilla_id,))

    return jsonify({"message": "Plantilla eliminada"})
