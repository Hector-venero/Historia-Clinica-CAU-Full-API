from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import disponibilidades_routes


def test_crear_disponibilidad_area_uses_own_user_and_normalizes_day(client, monkeypatch):
    login_as(client, MockUser(user_id=42, rol="area"))

    fake_cursor = FakeCursor(lastrowid=321)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(disponibilidades_routes, "get_connection", lambda: fake_connection)

    response = client.post(
        "/api/disponibilidades",
        json={
            "usuario_id": 999,
            "dia_semana": "Miércoles",
            "hora_inicio": "09:00",
            "hora_fin": "12:00",
            "activo": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["id"] == 321

    query, params = fake_cursor.executed[0]
    assert "INSERT INTO disponibilidades" in query
    assert params[0] == 42
    assert params[1] == "Miercoles"
    assert fake_connection.committed is True


def test_administrativo_puede_crear_su_disponibilidad(client, monkeypatch):
    login_as(client, MockUser(user_id=14, rol="administrativo"))

    fake_cursor = FakeCursor(lastrowid=55)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(disponibilidades_routes, "get_connection", lambda: fake_connection)

    response = client.post(
        "/api/disponibilidades",
        json={
            "dia_semana": "Lunes",
            "hora_inicio": "09:00",
            "hora_fin": "17:00",
            "activo": True,
        },
    )

    assert response.status_code == 201, "administrativo deberia poder configurar sus horarios"
    query, params = fake_cursor.executed[0]
    assert "INSERT INTO disponibilidades" in query
    assert params[0] == 14  # usa su propio usuario_id


def test_administrativo_puede_editar_disponibilidad(client, monkeypatch):
    login_as(client, MockUser(user_id=14, rol="administrativo"))

    fake_cursor = FakeCursor(fetchone_results=[{"usuario_id": 14}])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(disponibilidades_routes, "get_connection", lambda: fake_connection)

    response = client.put(
        "/api/disponibilidades/55",
        json={"hora_inicio": "10:00", "hora_fin": "18:00", "activo": True},
    )

    assert response.status_code == 200


def test_validar_disponibilidad_detecta_turnos_huerfanos(client, monkeypatch):
    login_as(client, MockUser(user_id=42, rol="profesional"))
    
    from datetime import datetime
    # Monday 2026-07-06 13:00 (Juan) -> falls outside [09:00-12:00], [14:00-17:00]
    # Tuesday 2026-07-07 10:00 (Pedro) -> falls inside [09:00-12:00]
    mock_turnos = [
        {
            "id": 1,
            "fecha_inicio": datetime(2026, 7, 6, 13, 0, 0),
            "fecha_fin": datetime(2026, 7, 6, 13, 20, 0),
            "motivo": "Rehabilitacion",
            "paciente": "Juan"
        },
        {
            "id": 2,
            "fecha_inicio": datetime(2026, 7, 7, 10, 0, 0),
            "fecha_fin": datetime(2026, 7, 7, 10, 20, 0),
            "motivo": "Control",
            "paciente": "Pedro"
        }
    ]
    
    fake_cursor = FakeCursor(fetchall_results=[mock_turnos])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(disponibilidades_routes, "get_connection", lambda: fake_connection)
    
    response = client.post(
        "/api/disponibilidades/validar",
        json={
            "usuario_id": 42,
            "disponibilidades": [
                {"dia_semana": "Lunes", "hora_inicio": "09:00", "hora_fin": "12:00", "activo": True},
                {"dia_semana": "Lunes", "hora_inicio": "14:00", "hora_fin": "17:00", "activo": True},
                {"dia_semana": "Martes", "hora_inicio": "09:00", "hora_fin": "12:00", "activo": True}
            ]
        }
    )
    
    assert response.status_code == 200
    res_data = response.get_json()
    
    # Only Turno 1 (Juan) should be flagged as orphan/out-of-bounds
    assert len(res_data) == 1
    assert res_data[0]["paciente"] == "Juan"
    assert "13:00" in res_data[0]["fecha"]
