"""Consultar quien accedio a que historia.

Escribir el registro es automatico (`app/accesos.py`); esto es lo que permite
leerlo. Sin una pantalla, la tabla existe pero nadie puede contestar la pregunta
para la que se creo.

**Solo la direccion.** Un registro de accesos dice, sobre cada persona del
equipo, a que hora abrio que historia. Es informacion sobre el personal, no solo
sobre los pacientes, y darsela a todo el mundo convierte una herramienta de
control en vigilancia lateral entre companeros.

⚠️ Un `profesional` **no** ve el registro ni siquiera de sus propios pacientes:
la lista incluye lo que hicieron sus colegas con esa misma historia.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required

from app import accesos
from app.utils.permisos import requiere_rol

bp_accesos = Blueprint("accesos", __name__)

# Cuantas filas devuelve como maximo. Es una pantalla de revision, no una
# exportacion: pedir diez mil accesos para mostrarlos en una tabla no ayuda a
# nadie y sostiene la conexion mientras tanto.
TOPE = 500


def _limite():
    pedido = request.args.get("limite", type=int) or 200
    return max(1, min(pedido, TOPE))


@bp_accesos.get("/api/pacientes/<int:paciente_id>/accesos")
@login_required
@requiere_rol("director")
def de_paciente(paciente_id):
    """Quien abrio la historia de este paciente."""
    return jsonify({"accesos": accesos.de_paciente(paciente_id, _limite())})


@bp_accesos.get("/api/usuarios/<int:usuario_id>/accesos")
@login_required
@requiere_rol("director")
def de_usuario(usuario_id):
    """A que historias accedio esta persona.

    Es la otra mitad de la pregunta, y en la practica la mas util: lo que se
    investiga no suele ser "quien vio esta historia" sino "que estuvo mirando
    esta persona".
    """
    return jsonify({"accesos": accesos.de_usuario(usuario_id, _limite())})
