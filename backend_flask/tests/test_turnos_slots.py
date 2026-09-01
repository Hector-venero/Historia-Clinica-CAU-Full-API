"""Alternativas cuando el horario pedido no está libre.

Rechazar con "el profesional no está disponible" y nada más obliga a quien
agenda a ir probando horarios a ciegas mientras el paciente espera. La respuesta
ahora incluye los próximos horarios libres de ese mismo día.
"""

from datetime import datetime, time, timedelta

import pytest

from app.routes import turnos_routes as tr
from conftest import MockUser, login_as, make_db

# Lunes
LUNES = datetime(2026, 9, 7, 9, 0)


def _franja(desde="09:00", hasta="12:00"):
    """Las horas vienen de MySQL como timedelta desde medianoche."""
    h1, m1 = map(int, desde.split(":"))
    h2, m2 = map(int, hasta.split(":"))
    return {
        "hora_inicio": timedelta(hours=h1, minutes=m1),
        "hora_fin": timedelta(hours=h2, minutes=m2),
    }


def _turno(desde, hasta):
    h1, m1 = map(int, desde.split(":"))
    h2, m2 = map(int, hasta.split(":"))
    return {
        "fecha_inicio": LUNES.replace(hour=h1, minute=m1),
        "fecha_fin": LUNES.replace(hour=h2, minute=m2),
    }


def _preparar(monkeypatch, franjas, ocupados, ausente=False, duracion=20):
    """Encadena las tres consultas que hace proximos_slots_libres."""
    monkeypatch.setattr(tr, "_obtener_duracion_turno", lambda _uid, _servicio_id=None: duracion)
    make_db(
        monkeypatch,
        tr,
        fetchall_results=[franjas, ocupados],
        fetchone_results=[{"1": 1} if ausente else None],
    )


def test_sugiere_los_primeros_horarios_de_la_franja(monkeypatch):
    _preparar(monkeypatch, [_franja()], [])

    libres = tr.proximos_slots_libres(1, LUNES)

    assert len(libres) == 3
    assert libres[0].startswith("2026-09-07T09:00")
    assert libres[1].startswith("2026-09-07T09:20")


def test_saltea_los_horarios_ocupados(monkeypatch):
    """Con 09:00-10:00 tomado, el primero libre es 10:00."""
    _preparar(monkeypatch, [_franja()], [_turno("09:00", "10:00")])

    libres = tr.proximos_slots_libres(1, LUNES)

    assert libres[0].startswith("2026-09-07T10:00")
    assert not any("T09:" in h for h in libres)


def test_no_sugiere_horarios_ya_pasados(monkeypatch):
    """Solo interesan los posteriores al momento pedido."""
    _preparar(monkeypatch, [_franja()], [])

    libres = tr.proximos_slots_libres(1, LUNES.replace(hour=10, minute=30))

    assert all(h >= "2026-09-07T10:40" for h in libres)


def test_sin_disponibilidad_no_sugiere_nada(monkeypatch):
    _preparar(monkeypatch, [], [])

    assert tr.proximos_slots_libres(1, LUNES) == []


def test_con_ausencia_todo_el_dia_no_sugiere_nada(monkeypatch):
    """No tiene sentido ofrecer horarios de un día que el profesional no trabaja."""
    _preparar(monkeypatch, [_franja()], [], ausente=True)

    assert tr.proximos_slots_libres(1, LUNES) == []


def test_no_sugiere_un_horario_que_no_entra_completo(monkeypatch):
    """Con la franja hasta las 12:00 y turnos de 20 min, 11:50 no entra."""
    _preparar(monkeypatch, [_franja("09:00", "12:00")], [])

    libres = tr.proximos_slots_libres(1, LUNES.replace(hour=11, minute=45))

    assert libres == []


def test_los_horarios_quedan_alineados_al_slot(monkeypatch):
    """Sugerir un horario que el backend luego movería sería contradictorio."""
    _preparar(monkeypatch, [_franja()], [])

    libres = tr.proximos_slots_libres(1, LUNES.replace(hour=9, minute=7))

    for horario in libres:
        minuto = int(horario[14:16])
        assert minuto % 20 == 0


def test_recorre_varias_franjas(monkeypatch):
    """Mañana y tarde con un corte al mediodía."""
    _preparar(
        monkeypatch,
        [_franja("09:00", "09:20"), _franja("14:00", "15:00")],
        [],
    )

    libres = tr.proximos_slots_libres(1, LUNES)

    assert libres[0].startswith("2026-09-07T09:00")
    assert libres[1].startswith("2026-09-07T14:00")


def test_respeta_la_cantidad_pedida(monkeypatch):
    _preparar(monkeypatch, [_franja("09:00", "18:00")], [])

    assert len(tr.proximos_slots_libres(1, LUNES, cantidad=5)) == 5


# ---------------------------------------------------------- ajuste de horario


def test_el_ajuste_se_informa_cuando_el_turno_se_movio():
    """El frontend lo necesita para avisar que el horario cambió."""
    original = datetime(2026, 9, 7, 10, 10)
    ajustado = datetime(2026, 9, 7, 10, 20)

    ajuste = tr._build_ajuste_payload(True, original, ajustado, ajustado)

    assert ajuste["aplicado"] is True
    assert "10:10" in ajuste["inicio_original"]
    assert "10:20" in ajuste["inicio_ajustado"]


def test_sin_ajuste_no_se_informa_nada():
    momento = datetime(2026, 9, 7, 10, 0)

    assert tr._build_ajuste_payload(False, momento, momento, momento) is None


@pytest.mark.parametrize(
    "pedido, esperado",
    [("10:00", "10:00"), ("10:01", "10:20"), ("10:19", "10:20"), ("10:20", "10:20")],
)
def test_el_horario_se_redondea_al_siguiente_slot(pedido, esperado):
    h, m = map(int, pedido.split(":"))
    resultado = tr._ceil_to_slot(LUNES.replace(hour=h, minute=m), 20)

    assert resultado.strftime("%H:%M") == esperado
