"""Los numeros del dia: que digan lo que el rotulo promete.

El resumen mostraba "Disponibles hoy" con `len(disponibilidad_hoy)`, que son las
**franjas de atencion configuradas**, no los lugares que quedan libres. Un
profesional con una sola franja de 09:00 a 17:00 y la agenda entera vacia veia
un 1. El rotulo prometia una cosa y el numero contaba otra.
"""

from app.routes import dashboard_routes as dr
from conftest import MockUser, login_as, make_db


def _dashboard(client, monkeypatch, rol, *, franjas, turnos, libres=None):
    """El dashboard hace muchas consultas encadenadas; solo importan estas."""
    monkeypatch.setattr(
        dr, "_agregar_comunicados", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        "app.routes.turnos_routes.proximos_slots_libres",
        lambda *a, **kw: libres or [],
    )

    # Las consultas devuelven, en orden: turnos del dia, proximo turno,
    # proxima ausencia, franjas, ausencias... y de ahi en mas listas vacias.
    make_db(
        monkeypatch, dr,
        fetchall_results=[turnos, franjas, [], [], [], [], [], []],
        fetchone_results=[None, None, None, None],
    )
    login_as(client, MockUser(1, rol))
    return client.get("/api/dashboard").get_json()


FRANJA = {"id": 1, "usuario_id": 1, "dia_semana": "Lunes", "hora_inicio": "09:00", "hora_fin": "17:00", "activo": 1}
TURNO = {"id": 1, "fecha_inicio": None, "fecha_fin": None, "motivo": "Control", "paciente_id": 1, "paciente": "Ana", "apellido": "Perez", "profesional": "Dr. Lopez"}


def test_el_profesional_ve_lugares_libres_y_no_franjas(client, monkeypatch):
    """Una franja de ocho horas con la agenda vacia no son "1 disponible"."""
    datos = _dashboard(
        client, monkeypatch, "profesional",
        franjas=[FRANJA], turnos=[TURNO],
        libres=[f"2026-09-01T{h:02d}:00:00-03:00" for h in range(9, 17)],
    )

    assert datos["resumen"]["lugares_libres_hoy"] == 8
    # La cuenta de franjas sigue estando, pero como lo que es.
    assert datos["resumen"]["franjas_hoy"] == 1
    assert "disponibilidad_hoy" not in datos["resumen"]


def test_sin_lugares_libres_el_numero_es_cero(client, monkeypatch):
    """Con el dia completo o ya terminado, cero es la respuesta correcta."""
    datos = _dashboard(client, monkeypatch, "profesional", franjas=[FRANJA], turnos=[], libres=[])

    assert datos["resumen"]["lugares_libres_hoy"] == 0


def test_quien_dirige_ve_cuanta_gente_atiende(client, monkeypatch):
    """Contar franjas daba 3 con un solo medico que atiende en tres bloques.

    La pregunta de quien dirige no es cuantas filas hay en la tabla de
    configuracion, sino cuanta gente esta atendiendo.
    """
    tres_bloques = [
        {**FRANJA, "id": 1, "usuario_id": 7},
        {**FRANJA, "id": 2, "usuario_id": 7},
        {**FRANJA, "id": 3, "usuario_id": 7},
    ]
    datos = _dashboard(client, monkeypatch, "director", franjas=tres_bloques, turnos=[])

    assert datos["resumen"]["profesionales_hoy"] == 1


def test_el_director_no_paga_el_calculo_de_lugares_libres(client, monkeypatch):
    """Serian tres consultas por cada profesional del centro, en el endpoint mas
    golpeado de la app."""
    datos = _dashboard(client, monkeypatch, "director", franjas=[FRANJA], turnos=[])

    assert "lugares_libres_hoy" not in datos["resumen"]
