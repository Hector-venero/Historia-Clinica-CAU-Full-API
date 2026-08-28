"""Lo que hace falta antes de autenticarse.

La pantalla de entrada tiene que poder mostrar el nombre y el logo del
consultorio, y eso ocurre cuando todavia no hay sesion. Es el unico dato que se
expone sin autenticar, y es deliberadamente minimo: nombre, nombre corto y logo.

No se devuelve el estado, ni el plan, ni los modulos: eso permitiria averiguar
como es la cuenta de un consultorio sin credenciales. Los modulos viajan en
/api/usuarios/me, con sesion.
"""

from flask import Blueprint, jsonify

from app import marca

bp_publico = Blueprint("publico", __name__, url_prefix="/api/publico")


@bp_publico.get("/marca")
def marca_publica():
    return jsonify(marca.publica())
