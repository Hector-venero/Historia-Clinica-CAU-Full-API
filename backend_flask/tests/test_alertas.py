# backend_flask/tests/test_alertas.py

import datetime
import pytest
from conftest import FakeConnection, FakeCursor
import app.utils.alertas as alertas
from app import mail, app

@pytest.fixture(autouse=True)
def app_context():
    with app.app_context():
        yield

def test_obtener_agenda_manana_vacia(client, monkeypatch):
    # Mockear DB para que retorne vacio en individuales y grupales
    fake_cursor = FakeCursor(fetchall_results=[[], []])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(alertas, "get_connection", lambda: fake_connection)
    
    fecha = datetime.date(2026, 7, 16)
    turnos_ind, turnos_grup = alertas.obtener_agenda_manana(usuario_id=1, fecha_manana=fecha)
    
    assert len(turnos_ind) == 0
    assert len(turnos_grup) == 0
    
    # Verificar queries ejecutadas
    assert len(fake_cursor.executed) == 2
    assert "FROM turnos" in fake_cursor.executed[0][0]
    assert "FROM turnos_grupales" in fake_cursor.executed[1][0]

def test_obtener_agenda_manana_con_datos(client, monkeypatch):
    mock_ind = [
        {
            "fecha_inicio": datetime.datetime(2026, 7, 17, 9, 0),
            "fecha_fin": datetime.datetime(2026, 7, 17, 9, 20),
            "motivo": "Kinesiologia",
            "observaciones": "Dolor lumbar",
            "nombre": "Juan",
            "apellido": "Perez"
        }
    ]
    
    mock_grup = [
        {
            "fecha_inicio": datetime.datetime(2026, 7, 17, 14, 0),
            "fecha_fin": datetime.datetime(2026, 7, 17, 15, 0),
            "observaciones": "Propiocepcion",
            "grupo_nombre": "Rehab Tobillo"
        }
    ]
    
    fake_cursor = FakeCursor(fetchall_results=[mock_ind, mock_grup])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(alertas, "get_connection", lambda: fake_connection)
    
    fecha = datetime.date(2026, 7, 17)
    turnos_ind, turnos_grup = alertas.obtener_agenda_manana(usuario_id=1, fecha_manana=fecha)
    
    assert len(turnos_ind) == 1
    assert turnos_ind[0]["nombre"] == "Juan"
    assert len(turnos_grup) == 1
    assert turnos_grup[0]["grupo_nombre"] == "Rehab Tobillo"

def test_generar_html_correo_vacio_y_con_datos(client):
    fecha_str = "Viernes 17/07/2026"
    
    # Caso 1: Vacio
    html_vacio = alertas.generar_html_correo("Dr. Test", fecha_str, [], [])
    assert "No tenés turnos programados para mañana" in html_vacio
    assert "Dr. Test" in html_vacio
    
    # Caso 2: Con datos
    mock_ind = [
        {
            "fecha_inicio": datetime.datetime(2026, 7, 17, 9, 0),
            "fecha_fin": datetime.datetime(2026, 7, 17, 9, 20),
            "motivo": "Kinesiologia",
            "observaciones": "Dolor lumbar",
            "nombre": "Juan",
            "apellido": "Perez"
        }
    ]
    mock_grup = [
        {
            "fecha_inicio": datetime.datetime(2026, 7, 17, 14, 0),
            "fecha_fin": datetime.datetime(2026, 7, 17, 15, 0),
            "observaciones": "Propiocepcion",
            "grupo_nombre": "Rehab Tobillo"
        }
    ]
    
    html_con_datos = alertas.generar_html_correo("Dr. Test", fecha_str, mock_ind, mock_grup)
    assert "📋 Turnos Individuales" in html_con_datos
    assert "Juan Perez" in html_con_datos
    assert "👥 Turnos Grupales" in html_con_datos
    assert "Rehab Tobillo" in html_con_datos

def test_procesar_y_enviar_alertas_flujo_completo(client, monkeypatch):
    # Mockear la consulta de profesionales disponibles
    mock_profesionales = [
        {"id": 1, "nombre": "Dr. House", "email": "house@cau.com"},
        {"id": 2, "nombre": "Dr. Chase", "email": "chase@cau.com"}
    ]
    
    fake_cursor = FakeCursor(fetchall_results=[mock_profesionales])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(alertas, "get_connection", lambda: fake_connection)
    
    # Mockear obtener_agenda_manana
    # House tendra turnos, Chase no tendra nada
    mock_turnos_house = (
        [{"fecha_inicio": datetime.datetime(2026, 7, 17, 9, 0), "fecha_fin": datetime.datetime(2026, 7, 17, 9, 20), "motivo": "Fisio", "observaciones": "", "nombre": "Pepe", "apellido": "Argento"}],
        []
    )
    mock_turnos_chase = ([], [])
    
    agenda_call_count = 0
    def mock_obtener_agenda(u_id, fecha_manana):
        nonlocal agenda_call_count
        agenda_call_count += 1
        if u_id == 1:
            return mock_turnos_house
        return mock_turnos_chase
        
    monkeypatch.setattr(alertas, "obtener_agenda_manana", mock_obtener_agenda)
    
    # Interceptador de mails enviados
    enviados = []
    monkeypatch.setattr(mail, "send", lambda msg: enviados.append(msg))
    
    resultado = alertas.procesar_y_enviar_alertas()
    
    assert agenda_call_count == 2
    assert len(enviados) == 2
    
    # Validar que los asuntos y destinatarios esten bien
    assert enviados[0].recipients == ["house@cau.com"]
    assert "Pepe Argento" in enviados[0].html
    
    assert enviados[1].recipients == ["chase@cau.com"]
    assert "No tenés turnos programados" in enviados[1].html

    assert resultado == {
        "profesionales": 2,
        "enviados": 2,
        "simulados": 0,
        "errores": 0,
    }


def test_procesar_alertas_dry_run_no_envia_correos(client, monkeypatch):
    profesionales = [{"id": 1, "nombre": "Dr. House", "email": "house@cau.com"}]
    fake_cursor = FakeCursor(fetchall_results=[profesionales])
    monkeypatch.setattr(alertas, "get_connection", lambda: FakeConnection(fake_cursor))
    monkeypatch.setattr(alertas, "obtener_agenda_manana", lambda *_: ([], []))
    monkeypatch.setattr(
        mail,
        "send",
        lambda _msg: pytest.fail("dry-run no debe enviar correos"),
    )

    resultado = alertas.procesar_y_enviar_alertas(dry_run=True)

    assert resultado == {
        "profesionales": 1,
        "enviados": 0,
        "simulados": 1,
        "errores": 0,
    }


def test_cli_alertas_imprime_resumen_verificable(client, monkeypatch):
    monkeypatch.setattr(
        alertas,
        "procesar_y_enviar_alertas",
        lambda dry_run=False: {
            "profesionales": 3,
            "enviados": 0 if dry_run else 3,
            "simulados": 3 if dry_run else 0,
            "errores": 0,
        },
    )

    result = app.test_cli_runner().invoke(args=["enviar-alertas", "--dry-run"])

    assert result.exit_code == 0
    assert "Proceso finalizado" in result.output
    assert "Simulados: 3" in result.output
