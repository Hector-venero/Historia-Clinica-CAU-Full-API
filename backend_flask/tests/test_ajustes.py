"""Los avisos del consultorio, que hasta ahora se mandaban siempre.

Un consultorio que ya avisa por WhatsApp le mandaba al paciente dos
confirmaciones del mismo turno, y no habia pantalla que lo evitara.

Lo que estos tests fijan, y es lo unico realmente delicado:

**Ante la duda se avisa.** Sin fila, con la tabla sin migrar o con la base
caida, el aviso sale. Dejar de avisarle a un paciente por un problema del
sistema es mucho peor que mandar un correo de mas — el paciente no se entera de
que el turno existe y falta.
"""

import pytest

from app import ajustes
from app.routes import marca_routes as mr
from conftest import MockUser, login_as, make_db


# --------------------------------------------------------- valores por defecto


def test_sin_fila_el_aviso_sale(monkeypatch):
    """Un consultorio que actualiza el sistema no puede dejar de avisar porque
    aparecio un interruptor que nunca toco."""
    make_db(monkeypatch, ajustes, fetchone_results=[None])

    assert ajustes.activo("avisar_turno_nuevo") is True


def test_todos_los_avisos_vienen_encendidos():
    for clave, definicion in ajustes.AJUSTES.items():
        assert definicion["defecto"] is True, f"'{clave}' viene apagado"


def test_una_clave_desconocida_no_apaga_nada(monkeypatch):
    """Si alguien consulta un aviso que ya no existe, se manda igual."""
    make_db(monkeypatch, ajustes)

    assert ajustes.activo("aviso_que_no_existe") is True


def test_si_la_base_falla_el_aviso_sale(monkeypatch):
    """La tabla puede no estar migrada todavia, o la base caida."""
    _conn, cur = make_db(
        monkeypatch, ajustes, execute_side_effects=[RuntimeError("sin tabla")]
    )

    assert ajustes.activo("avisar_turno_nuevo") is True


def test_todos_cae_a_los_defectos_si_falla_la_consulta(monkeypatch):
    make_db(monkeypatch, ajustes, execute_side_effects=[RuntimeError("sin tabla")])

    estado = ajustes.todos()

    assert estado == {c: d["defecto"] for c, d in ajustes.AJUSTES.items()}


# ------------------------------------------------------------ apagar y prender


def test_apagado_el_aviso_no_sale(monkeypatch):
    make_db(monkeypatch, ajustes, fetchone_results=[{"valor": "no"}])

    assert ajustes.activo("avisar_turno_nuevo") is False


def test_encendido_el_aviso_sale(monkeypatch):
    make_db(monkeypatch, ajustes, fetchone_results=[{"valor": "si"}])

    assert ajustes.activo("avisar_turno_nuevo") is True


def test_guardar_ignora_lo_que_no_conoce(monkeypatch):
    """El cuerpo viene del pedido: no se escribe cualquier clave en la tabla."""
    _conn, cur = make_db(monkeypatch, ajustes, fetchall_results=[[]])

    ajustes.guardar({"avisar_turno_nuevo": False, "borrar_todo": True})

    escritas = [q for q in cur.queries if "INSERT INTO configuracion" in q]
    assert len(escritas) == 1
    assert cur.executed[0][1][0] == "avisar_turno_nuevo"


def test_se_guarda_como_texto_legible(monkeypatch):
    """La fila se entiende leyendola, sin traducir un 0/1."""
    _conn, cur = make_db(monkeypatch, ajustes, fetchall_results=[[]])

    ajustes.guardar({"avisar_turno_cancelado": False})

    assert cur.executed[0][1] == ("avisar_turno_cancelado", "no")


# ------------------------------------------------- lo que respetan los envios


def test_el_correo_de_confirmacion_respeta_el_interruptor(monkeypatch):
    """Es el punto del cambio: antes salia siempre."""
    from app.utils import mails_turnos

    monkeypatch.setattr(ajustes, "activo", lambda clave: False)

    enviado = mails_turnos.enviar_confirmacion(
        {"email": "quien@ejemplo.com", "nombre": "Ana"},
        {"nombre": "Dr. Lopez"},
        "2026-09-15 10:00:00",
        "2026-09-15 10:30:00",
    )

    assert enviado is False


def test_el_correo_de_cancelacion_respeta_el_interruptor(monkeypatch):
    from app.utils import mails_turnos

    monkeypatch.setattr(ajustes, "activo", lambda clave: False)

    enviado = mails_turnos.enviar_cancelacion(
        {"email": "quien@ejemplo.com", "nombre": "Ana"},
        "Dr. Lopez",
        "2026-09-15 10:00:00",
    )

    assert enviado is False


# ------------------------------------------------------------------- permisos


def test_un_administrativo_los_ve_pero_no_los_cambia(client, monkeypatch):
    """Puede necesitar saber por que un paciente no recibio el correo; decidir
    que el consultorio deje de avisar es de la direccion."""
    login_as(client, MockUser(1, "administrativo"))
    make_db(monkeypatch, mr)
    make_db(monkeypatch, ajustes, fetchall_results=[[]])

    assert client.get("/api/ajustes").status_code == 200
    assert client.put("/api/ajustes", json={"avisar_turno_nuevo": False}).status_code == 403


def test_un_profesional_no_los_ve(client, monkeypatch):
    login_as(client, MockUser(1, "profesional"))
    make_db(monkeypatch, mr)

    assert client.get("/api/ajustes").status_code == 403
