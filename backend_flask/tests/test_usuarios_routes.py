import io
import os
import pytest
from PIL import Image
from conftest import FakeConnection, FakeCursor, MockUser, login_as
from app.routes import usuarios_routes

def test_actualizar_perfil_sin_foto(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol='profesional'))

    fake_cursor = FakeCursor()
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(usuarios_routes, 'get_connection', lambda: fake_connection)
    monkeypatch.setattr(usuarios_routes, '_professional_values', lambda form: {})

    response = client.post('/api/usuario/perfil', data={
        'nombre': 'Nuevo Nombre',
        'email': 'nuevo@example.com'
    })

    assert response.status_code == 200
    assert response.get_json()['message'] == 'Perfil actualizado correctamente.'
    assert fake_connection.committed is True

def test_actualizar_perfil_con_foto_valida(client, monkeypatch, tmp_path):
    login_as(client, MockUser(user_id=1, rol='profesional'))

    # Mock database
    fake_cursor = FakeCursor()
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(usuarios_routes, 'get_connection', lambda: fake_connection)
    monkeypatch.setattr(usuarios_routes, '_professional_values', lambda form: {})

    # Create a real small 1x1 image in memory
    img = Image.new('RGB', (1, 1), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    # We mock carpeta_fotos inside the module (wait, since it is a local variable in the function,
    # we can't monkeypatch it directly, but let's see how we can handle this or if it fails on Windows)
    response = client.post('/api/usuario/perfil', data={
        'nombre': 'Nuevo Nombre',
        'email': 'nuevo@example.com',
        'foto': (img_byte_arr, 'test.jpg')
    })

    # Let's see what status code we get and if it fails due to the hardcoded path.
    # We will check if it fails or succeeds.
    print("Response data:", response.data)
    assert response.status_code == 200


def test_actualizar_perfil_con_foto_invalida(client, monkeypatch, tmp_path):
    login_as(client, MockUser(user_id=1, rol='profesional'))

    fake_cursor = FakeCursor()
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(usuarios_routes, 'get_connection', lambda: fake_connection)
    monkeypatch.setattr(usuarios_routes, '_professional_values', lambda form: {})

    # Upload invalid image data (text file)
    invalid_data = io.BytesIO(b"this is not an image file, it is plain text")

    response = client.post('/api/usuario/perfil', data={
        'nombre': 'Nuevo Nombre',
        'email': 'nuevo@example.com',
        'foto': (invalid_data, 'test.txt')
    })

    assert response.status_code == 200

    # Let's check the size of the saved file.
    saved_path = os.path.join(usuarios_routes.app.root_path, "static", "fotos_usuarios", "user_1.txt")
    assert os.path.exists(saved_path)
    size = os.path.getsize(saved_path)
    print(f"Saved file size: {size}")
    # If it didn't call seek(0), the saved file will be 0 bytes (empty)!
    assert size > 0
    os.remove(saved_path)

