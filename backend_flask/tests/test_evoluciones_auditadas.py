from conftest import FakeConnection, FakeCursor, MockUser, login_as
from app.routes import pacientes_routes

def test_editar_evolucion_sin_permisos_devuelve_403(client, monkeypatch):
    # Intentar editar con un profesional que no es el autor
    login_as(client, MockUser(user_id=9, rol="profesional"))

    # Mock de evolucion original: paciente_id=1, id=50, usuario_id=5 (otro profesional)
    evo_original = {
        'id': 50,
        'paciente_id': 1,
        'fecha': '2026-07-10',
        'contenido': 'Evolucion inicial',
        'indicaciones': 'Reposo',
        'usuario_id': 5,
        'padre_id': None,
        'version': 1,
        'activo': 1
    }

    # Fetchone devuelve la evolucion original
    fake_cursor = FakeCursor(fetchone_results=[evo_original])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)

    response = client.put(
        "/api/pacientes/1/evolucion/50",
        data={
            "fecha": "2026-07-16",
            "contenido": "Contenido editado",
            "indicaciones": "Nuevas indicaciones"
        }
    )

    assert response.status_code == 403
    assert "permisos" in response.get_json()["error"].lower()


def test_editar_evolucion_autor_ok_devuelve_200(client, monkeypatch):
    # Loguearse como el autor (user_id=5)
    login_as(client, MockUser(user_id=5, rol="profesional"))

    evo_original = {
        'id': 50,
        'paciente_id': 1,
        'fecha': '2026-07-10',
        'contenido': 'Evolucion inicial',
        'indicaciones': 'Reposo',
        'usuario_id': 5,
        'padre_id': None,
        'version': 1,
        'activo': 1
    }

    # fetchone_results:
    # 1. SELECT de la evolucion actual
    # 2. SELECT MAX(version)
    # 3. SELECT filename de archivos adjuntos viejos
    fake_cursor = FakeCursor(
        fetchone_results=[
            evo_original,
            {'max_v': 1}
        ],
        fetchall_results=[[]] # No hay archivos adjuntos anteriores
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    
    # Mockear las funciones de hashing/blockchain para evitar fallos de conexion
    monkeypatch.setattr(pacientes_routes, "actualizar_hash_evolucion", lambda x: "hash-falso")
    monkeypatch.setattr(pacientes_routes, "actualizar_historia", lambda x, y: "hash-consolidado")

    response = client.put(
        "/api/pacientes/1/evolucion/50",
        data={
            "fecha": "2026-07-16",
            "contenido": "Contenido editado por el autor",
            "indicaciones": "Nuevas indicaciones del autor"
        }
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "editada" in payload["message"].lower()
    assert fake_connection.committed is True

    # Verificar que se inserto el nuevo registro con version 2
    queries = [q for q, p in fake_cursor.executed]
    insert_query = [q for q in queries if "INSERT INTO evoluciones" in q][0]
    update_query = [q for q in queries if "UPDATE evoluciones" in q][0]

    assert insert_query is not None
    assert update_query is not None


def test_editar_evolucion_director_ok_devuelve_200(client, monkeypatch):
    # Loguearse como Director (user_id=10, rol=director)
    login_as(client, MockUser(user_id=10, rol="director"))

    evo_original = {
        'id': 50,
        'paciente_id': 1,
        'fecha': '2026-07-10',
        'contenido': 'Evolucion inicial',
        'indicaciones': 'Reposo',
        'usuario_id': 5, # Escrita por otro profesional
        'padre_id': None,
        'version': 1,
        'activo': 1
    }

    fake_cursor = FakeCursor(
        fetchone_results=[
            evo_original,
            {'max_v': 1}
        ],
        fetchall_results=[[]]
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)

    # Mockear hashing
    monkeypatch.setattr(pacientes_routes, "actualizar_hash_evolucion", lambda x: "hash-falso")
    monkeypatch.setattr(pacientes_routes, "actualizar_historia", lambda x, y: "hash-consolidado")

    response = client.put(
        "/api/pacientes/1/evolucion/50",
        data={
            "fecha": "2026-07-16",
            "contenido": "Contenido editado por director",
            "indicaciones": "Nuevas indicaciones del director"
        }
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "editada" in payload["message"].lower()
    assert fake_connection.committed is True


def test_get_historial_evolucion_retorna_secuencia(client, monkeypatch):
    login_as(client, MockUser(user_id=5, rol="profesional"))

    evo_original = {
        'id': 50,
        'padre_id': None
    }

    # Query de historial
    historial_versiones = [
        {
            'id': 50, 'fecha': '2026-07-10', 'contenido': 'Original', 'indicaciones': '',
            'creado_en': '2026-07-10 10:00:00', 'version': 1, 'activo': 0, 'nombre_usuario': 'Juan', 'especialidad_usuario': 'Cardiologo'
        },
        {
            'id': 51, 'fecha': '2026-07-16', 'contenido': 'Editado', 'indicaciones': '',
            'creado_en': '2026-07-16 10:00:00', 'version': 2, 'activo': 1, 'nombre_usuario': 'Juan', 'especialidad_usuario': 'Cardiologo'
        }
    ]

    fake_cursor = FakeCursor(
        fetchone_results=[evo_original],
        fetchall_results=[
            historial_versiones,
            [], # Archivos adjuntos para version 1
            []  # Archivos adjuntos para version 2
        ]
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)

    response = client.get("/api/pacientes/1/evolucion/50/historial")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 2
    assert payload[0]['version'] == 1
    assert payload[1]['version'] == 2
    assert payload[0]['activo'] == 0
    assert payload[1]['activo'] == 1
