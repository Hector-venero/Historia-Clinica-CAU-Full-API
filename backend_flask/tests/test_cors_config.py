import pytest

from app import build_cors_origins


def test_production_cors_only_allows_frontend_url():
    assert build_cors_origins(
        environment="production",
        frontend_url="https://cau.example.ar/",
        configured_origins="",
    ) == ["https://cau.example.ar"]


def test_development_cors_keeps_local_origins():
    origins = build_cors_origins(
        environment="development",
        frontend_url="http://localhost:5173",
        configured_origins="",
    )

    assert "http://localhost:5173" in origins
    assert "http://localhost" in origins
    assert "http://localhost:4173" in origins


def test_explicit_cors_origins_override_defaults():
    assert build_cors_origins(
        environment="production",
        frontend_url="https://cau.example.ar",
        configured_origins="https://admin.example.com/, https://cau.example.ar",
    ) == ["https://admin.example.com", "https://cau.example.ar"]


def test_unknown_origin_receives_no_cors_header(client):
    response = client.get(
        "/api/health/public",
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_request_without_origin_never_receives_wildcard(client):
    """Una request sin Origin puede traer ACAO, pero nunca '*'.

    flask-cors 6.x responde con el primer origen permitido cuando la request no
    manda Origin. Es inocuo: el navegador solo aplica CORS a peticiones
    cross-origin, y esas siempre mandan Origin; una same-origin ignora el header.
    Lo que si seria un agujero es un comodin, porque combinado con
    supports_credentials habilitaria a cualquier sitio a leer la respuesta.
    """
    response = client.get("/api/health/public")

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") != "*"


def test_production_rejects_non_https_frontend_url():
    """En produccion FRONTEND_URL tiene que ser HTTPS: se falla, no se degrada."""
    with pytest.raises(RuntimeError):
        build_cors_origins(
            environment="production",
            frontend_url="http://cau.example.ar",
            configured_origins="",
        )
