"""Consentimiento en el alta: la casilla del navegador no prueba nada.

Hoy no hay textos publicados, asi que no se exige nada — pedirle a alguien que
acepte un borrador no consiente. Lo que estos tests fijan es que **cuando se
publiquen**, el servidor los exija de verdad y no alcance con marcar la casilla
en el frontend.
"""

import pytest

from app import portal, registro


# --------------------------------------------------- mientras no hay textos


def test_sin_terminos_publicados_no_se_exige_nada():
    """Es el estado de hoy: el alta no puede quedar bloqueada por un borrador."""
    assert registro.TERMINOS_VERSION_VIGENTE is None
    assert registro._validar_terminos({}) is None
    assert portal._validar_terminos({}) is None


# ------------------------------------------------- cuando se publiquen


def test_el_alta_de_consultorio_exige_la_version_vigente(monkeypatch):
    monkeypatch.setattr(registro, "TERMINOS_VERSION_VIGENTE", "1.0")

    with pytest.raises(registro.ErrorRegistro):
        registro._validar_terminos({})

    assert registro._validar_terminos({"terminos_version": "1.0"}) == "1.0"


def test_una_version_vieja_no_alcanza(monkeypatch):
    """Aceptar los terminos de hace un ano no es aceptar los de ahora.

    Es todo el motivo por el que se guarda la version y no un simple `si`.
    """
    monkeypatch.setattr(registro, "TERMINOS_VERSION_VIGENTE", "2.0")

    with pytest.raises(registro.ErrorRegistro):
        registro._validar_terminos({"terminos_version": "1.0"})


def test_el_alta_de_paciente_tambien_lo_exige(monkeypatch):
    monkeypatch.setattr(portal, "TERMINOS_VERSION_VIGENTE", "1.0")

    with pytest.raises(portal.ErrorPortal):
        portal._validar_terminos({"terminos_version": ""})

    assert portal._validar_terminos({"terminos_version": "1.0"}) == "1.0"


def test_los_dos_planos_validan_por_separado():
    """El portal no importa el modulo de la plataforma: son planos distintos y
    cruzarlos por un dato de presentacion no vale el acople."""
    assert registro._validar_terminos is not portal._validar_terminos
