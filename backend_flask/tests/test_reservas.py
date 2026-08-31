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


# ------------------------------------------------------------ cancelacion


def test_no_se_cancela_un_turno_ya_cancelado(monkeypatch):
    fila = {"estado": "cancelado", "fecha_inicio": None}
    monkeypatch.setattr(reservas, "_puede_cancelarse", lambda f: False)

    class _Ctx:
        def __enter__(self):
            class _Cur:
                def execute(self, *a, **k):
                    pass

                def fetchone(self):
                    return fila
            return (None, _Cur())

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(reservas.portal, "cursor_portal", lambda commit=False: _Ctx())

    with flask_app.test_request_context("/"):
        with pytest.raises(reservas.ErrorReserva) as exc:
            reservas.cancelar(_PacienteFalso(), 1)

    assert "ya estaba cancelado" in str(exc.value)


def test_no_se_cancela_sobre_la_hora():
    """Una cancelacion de ultimo momento que entra al sistema y nadie mira es
    peor que un llamado: el consultorio sigue esperando al paciente igual."""
    from datetime import datetime, timedelta

    sobre_la_hora = {
        "estado": "reservado",
        "fecha_inicio": datetime.now() + timedelta(hours=1),
    }
    assert reservas._puede_cancelarse(sobre_la_hora) is False


def test_si_se_cancela_con_anticipacion():
    from datetime import datetime, timedelta

    con_tiempo = {
        "estado": "reservado",
        "fecha_inicio": datetime.now() + timedelta(days=3),
    }
    assert reservas._puede_cancelarse(con_tiempo) is True


def test_un_turno_cancelado_no_se_puede_volver_a_cancelar():
    from datetime import datetime, timedelta

    cancelado = {
        "estado": "cancelado",
        "fecha_inicio": datetime.now() + timedelta(days=3),
    }
    assert reservas._puede_cancelarse(cancelado) is False


def test_la_ventana_de_cancelacion_es_mayor_que_la_de_reserva():
    """Poder reservar algo que ya no se puede cancelar seria una trampa."""
    assert reservas.HORAS_MINIMAS_CANCELACION >= reservas.HORAS_MINIMAS_ANTICIPACION


class _PacienteFalso:
    tipo_documento = "DNI"
    numero_documento = "30111222"
    nombre = "Ana"
    apellido = "Perez"
    email = "ana@ejemplo.com"
    telefono = None


# ------------------------------------------ el proximo dia con lugar


def _sin_horarios_salvo(monkeypatch, fecha_con_lugar, horarios=("09:00", "09:45")):
    """horarios_libres() falso: solo un dia tiene lugar."""
    llamadas = []

    def falso(cliente_id, usuario_id, fecha, cantidad=20):
        llamadas.append(fecha)
        if fecha == fecha_con_lugar:
            return [f"{fecha}T{h}:00-03:00" for h in horarios]
        return []

    monkeypatch.setattr(reservas, "horarios_libres", falso)
    return llamadas


def test_devuelve_el_primer_dia_con_lugar(monkeypatch):
    """El portal dejaba a la persona adivinando dia por dia."""
    from datetime import date, timedelta

    objetivo = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
    _sin_horarios_salvo(monkeypatch, objetivo)

    encontrado = reservas.proximo_dia_con_lugar(1, 1)

    assert encontrado["fecha"] == objetivo
    assert len(encontrado["horarios"]) == 2


def test_corta_en_el_primero_y_no_sigue_consultando(monkeypatch):
    """Cada dia es una consulta a la base: seguir despues de encontrarlo seria
    trabajo tirado."""
    from datetime import date, timedelta

    objetivo = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    llamadas = _sin_horarios_salvo(monkeypatch, objetivo)

    reservas.proximo_dia_con_lugar(1, 1)

    assert llamadas[-1] == objetivo


def test_no_mira_mas_alla_de_la_ventana(monkeypatch):
    """Recorrer los 60 dias de anticipacion serian 60 consultas para responder
    una sola pregunta."""
    llamadas = _sin_horarios_salvo(monkeypatch, "1999-01-01")

    assert reservas.proximo_dia_con_lugar(1, 1) is None
    assert len(llamadas) == reservas.DIAS_QUE_SE_MIRAN_ADELANTE


def test_arranca_desde_el_dia_pedido(monkeypatch):
    from datetime import date, timedelta

    desde = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
    llamadas = _sin_horarios_salvo(monkeypatch, "1999-01-01")

    reservas.proximo_dia_con_lugar(1, 1, desde=desde)

    assert llamadas[0] == desde


def test_un_dia_pasado_no_hace_mirar_hacia_atras(monkeypatch):
    """Pedir el 2020 no puede ofrecer horarios que ya pasaron."""
    from datetime import date

    llamadas = _sin_horarios_salvo(monkeypatch, "1999-01-01")

    reservas.proximo_dia_con_lugar(1, 1, desde="2020-01-01")

    assert llamadas[0] == date.today().strftime("%Y-%m-%d")


def test_una_fecha_invalida_se_rechaza(monkeypatch):
    _sin_horarios_salvo(monkeypatch, "1999-01-01")

    with pytest.raises(reservas.ErrorReserva):
        reservas.proximo_dia_con_lugar(1, 1, desde="el jueves")
