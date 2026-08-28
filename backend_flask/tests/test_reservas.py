"""Reserva de turnos desde el portal: el cruce de planos.

Lo que se puede probar sin MySQL: que el cambio de contexto restaure siempre, y
las reglas de anticipacion. Que dos reservas simultaneas no entren las dos se
verifica contra el stack, porque ahi lo que importa es la restriccion real de la
base.
"""

import pytest
from flask import g

from app import app as flask_app
from app import reservas


class _ClienteFalso:
    def __init__(self, slug="drlopez"):
        self.id = 1
        self.slug = slug
        self.nombre = f"Consultorio {slug}"
        self.estado = "activo"
        self.activo = True
        self.config = {}


# ------------------------------------------------- el cambio de contexto


def test_el_contexto_se_restaura_al_salir():
    """Es lo que evita que el resto del pedido quede apuntando a otra base."""
    anterior = _ClienteFalso("original")

    with flask_app.test_request_context("/"):
        g.cliente = anterior

        with reservas.como_consultorio(_ClienteFalso("destino")):
            assert g.cliente.slug == "destino"

        assert g.cliente.slug == "original"


def test_el_contexto_se_restaura_aunque_falle():
    """Sin el finally, una excepcion dejaria el pedido apuntando a la base de
    otro consultorio: exactamente la fuga que toda la arquitectura evita."""
    anterior = _ClienteFalso("original")

    with flask_app.test_request_context("/"):
        g.cliente = anterior

        with pytest.raises(RuntimeError):
            with reservas.como_consultorio(_ClienteFalso("destino")):
                raise RuntimeError("algo se rompio en el medio")

        assert g.cliente.slug == "original"


def test_el_contexto_anidado_vuelve_al_intermedio():
    with flask_app.test_request_context("/"):
        g.cliente = _ClienteFalso("a")

        with reservas.como_consultorio(_ClienteFalso("b")):
            with reservas.como_consultorio(_ClienteFalso("c")):
                assert g.cliente.slug == "c"
            assert g.cliente.slug == "b"

        assert g.cliente.slug == "a"


def test_sin_cliente_previo_vuelve_a_none():
    """El portal atiende sin inquilino resuelto: al salir tiene que quedar como
    estaba, o el resto del pedido creeria pertenecer a un consultorio."""
    with flask_app.test_request_context("/"):
        g.cliente = None

        with reservas.como_consultorio(_ClienteFalso()):
            assert g.cliente is not None

        assert g.cliente is None


# ------------------------------------------------------ reglas de reserva


def test_un_profesional_que_no_publico_su_agenda_no_es_reservable(monkeypatch):
    """Mismo mensaje que si no existiera: no tiene que ser descubrible probando
    ids."""
    monkeypatch.setattr(reservas, "profesional_publico", lambda c, u: None)

    with flask_app.test_request_context("/"):
        with pytest.raises(reservas.ErrorReserva) as exc:
            reservas.horarios_libres(1, 99, "2026-09-15")

    assert "no acepta turnos online" in str(exc.value)


def test_una_fecha_invalida_se_rechaza(monkeypatch):
    monkeypatch.setattr(
        reservas, "profesional_publico", lambda c, u: {"consultorio_slug": "drlopez"}
    )
    monkeypatch.setattr(reservas.plataforma, "buscar_por_slug", lambda s: _ClienteFalso())

    with flask_app.test_request_context("/"):
        with pytest.raises(reservas.ErrorReserva):
            reservas.horarios_libres(1, 1, "no-es-una-fecha")


def test_un_dia_pasado_no_ofrece_horarios(monkeypatch):
    monkeypatch.setattr(
        reservas, "profesional_publico", lambda c, u: {"consultorio_slug": "drlopez"}
    )
    monkeypatch.setattr(reservas.plataforma, "buscar_por_slug", lambda s: _ClienteFalso())

    with flask_app.test_request_context("/"):
        assert reservas.horarios_libres(1, 1, "2020-01-01") == []


def test_no_se_reserva_mas_alla_del_limite(monkeypatch):
    """Sin limite, alguien ocupa un horario de dentro de tres anios que el
    profesional todavia no sabe si va a trabajar."""
    from datetime import datetime, timedelta

    lejos = (datetime.now() + timedelta(days=reservas.DIAS_MAXIMOS_ANTICIPACION + 10)).strftime("%Y-%m-%d")

    monkeypatch.setattr(
        reservas, "profesional_publico", lambda c, u: {"consultorio_slug": "drlopez"}
    )
    monkeypatch.setattr(reservas.plataforma, "buscar_por_slug", lambda s: _ClienteFalso())

    with flask_app.test_request_context("/"):
        with pytest.raises(reservas.ErrorReserva) as exc:
            reservas.horarios_libres(1, 1, lejos)

    assert str(reservas.DIAS_MAXIMOS_ANTICIPACION) in str(exc.value)


def test_un_consultorio_suspendido_no_recibe_reservas(monkeypatch):
    """Cortar el acceso por falta de pago no puede dejar que le sigan entrando
    turnos que nadie va a atender."""
    suspendido = _ClienteFalso()
    suspendido.estado = "suspendido"
    suspendido.activo = False

    monkeypatch.setattr(
        reservas, "profesional_publico", lambda c, u: {"consultorio_slug": "drlopez"}
    )
    monkeypatch.setattr(reservas.plataforma, "buscar_por_slug", lambda s: suspendido)

    with flask_app.test_request_context("/"):
        with pytest.raises(reservas.ErrorReserva) as exc:
            reservas.horarios_libres(1, 1, "2026-09-15")

    assert "no esta disponible" in str(exc.value)


def test_los_limites_de_anticipacion_son_coherentes():
    """Un minimo mayor que el maximo dejaria sin poder reservar nunca."""
    assert reservas.HORAS_MINIMAS_ANTICIPACION > 0
    assert reservas.DIAS_MAXIMOS_ANTICIPACION > 0
    assert reservas.HORAS_MINIMAS_ANTICIPACION < reservas.DIAS_MAXIMOS_ANTICIPACION * 24
