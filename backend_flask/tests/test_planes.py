"""Que el plan encienda modulos.

Hasta ahora `clientes.plan` era un texto que **no se traducia a modulos en
ninguna parte**. Los modulos vivian sueltos en `clientes_config.modulos`, la
unica forma de cambiarlos era escribir la base a mano, y contratar el plan
grande no cambiaba ni una pantalla. Vender un plan y no tener escrito en ningun
lado que incluye es como no tener planes.

Lo que estos tests fijan:

1. El orden de resolucion: override de la fila, despues el plan, y todo en la
   instalacion de un solo centro. El tercer caso es el que mantiene vivo al CAU
   con este mismo codigo.
2. Que un plan desconocido caiga al **chico**. Equivocarse para arriba regala lo
   que se vende y no lo reclama nadie, asi que no se entera nadie.
3. Que las claves de plan sean las mismas que las de la pagina de precios: dos
   vocabularios es como empieza a venderse una cosa y entregarse otra.
"""

import pytest

from app import marca


class ClienteFalso:
    """Lo minimo que `marca` le pide al cliente resuelto."""

    def __init__(self, plan=None, config=None):
        self.plan = plan
        self.config = config


@pytest.fixture
def como(monkeypatch):
    """Pone (o saca) el consultorio del pedido en curso."""

    def _poner(cliente):
        monkeypatch.setattr(marca, "_cliente", lambda: cliente)

    return _poner


# --------------------------------------------------- de donde salen los modulos


def test_sin_consultorio_esta_todo_habilitado(como):
    """La instalacion de un solo centro no tiene planes, y no puede perder nada."""
    como(None)

    assert marca.modulos() == set(marca.MODULOS_CONOCIDOS)
    assert marca.blockchain_habilitado() is True
    assert marca.plan() is None


def test_el_plan_chico_no_trae_los_modulos_del_grande(como):
    como(ClienteFalso(plan="profesional"))

    modulos = marca.modulos()
    assert "recetas" in modulos
    assert "grupos" not in modulos
    assert "comunicados" not in modulos
    assert marca.blockchain_habilitado() is False


def test_el_plan_grande_los_enciende(como):
    """Es la prueba de que contratar el plan grande cambia algo."""
    como(ClienteFalso(plan="equipo"))

    modulos = marca.modulos()
    assert {"grupos", "comunicados", "blockchain"} <= modulos
    assert marca.blockchain_habilitado() is True


def test_basico_es_el_nombre_viejo_del_plan_chico(como):
    """Lo puso el script de alta antes de que existiera el mapa.

    Se conserva como sinonimo en vez de renombrarlo: renombrar es una migracion
    sobre clientes vivos para arreglar un alias.
    """
    como(ClienteFalso(plan="basico"))

    assert marca.modulos() == set(marca.PLANES["profesional"]["modulos"])
    assert marca.plan()["nombre"] == "Profesional"


def test_un_plan_desconocido_cae_al_chico(como):
    """Para abajo y no para arriba: regalar lo que se vende no lo reclama nadie."""
    como(ClienteFalso(plan="promo-verano-2027"))

    assert marca.modulos() == set(marca.PLANES[marca.PLAN_POR_DEFECTO]["modulos"])
    assert "blockchain" not in marca.modulos()


def test_la_fila_de_configuracion_pisa_al_plan(como):
    """El override existe para vender un modulo suelto sin inventar un plan."""
    como(ClienteFalso(plan="profesional", config={"modulos": "turnos,comunicados"}))

    assert marca.modulos() == {"turnos", "comunicados"}


def test_la_configuracion_vacia_no_pisa_nada(como):
    """Una cadena vacia es "no configurado", no "ningun modulo".

    Al reves, un consultorio con la fila creada y la columna en blanco se
    quedaria sin sistema.
    """
    como(ClienteFalso(plan="equipo", config={"modulos": ""}))

    assert "grupos" in marca.modulos()


# ------------------------------------------------------- lo que no esta incluido


def test_se_sabe_que_falta_para_poder_ofrecerlo(como):
    """No se esconde lo que no se contrato: se muestra con candado.

    Un consultorio que nunca ve que existen los comunicados no los va a
    contratar nunca.
    """
    como(ClienteFalso(plan="profesional"))

    faltantes = marca.modulos_no_incluidos()
    assert "grupos" in faltantes
    assert "recetas" not in faltantes
    assert not (set(faltantes) & marca.modulos())


def test_al_plan_grande_no_le_falta_nada(como):
    como(ClienteFalso(plan="equipo"))

    assert marca.modulos_no_incluidos() == []


# ------------------------------------------------------------------ vocabulario


def test_los_planes_se_llaman_igual_que_en_la_pagina_de_precios():
    """`publico/datos.js` → PLANES usa 'profesional' y 'equipo'.

    Si el sistema y el sitio usan dos vocabularios, se termina vendiendo una
    cosa y entregando otra. Este test es el unico lugar donde eso se nota.
    """
    assert {"profesional", "equipo"} <= set(marca.PLANES)


def test_ningun_plan_promete_un_modulo_que_no_existe():
    for clave, definicion in marca.PLANES.items():
        desconocidos = set(definicion["modulos"]) - set(marca.MODULOS_CONOCIDOS)
        assert not desconocidos, f"El plan '{clave}' promete {desconocidos}"


def test_todo_plan_tiene_nombre_para_mostrar():
    """El plan se le muestra a quien lo paga."""
    for clave in marca.PLANES:
        assert marca.NOMBRE_DE_PLAN.get(clave), f"Falta el nombre de '{clave}'"
