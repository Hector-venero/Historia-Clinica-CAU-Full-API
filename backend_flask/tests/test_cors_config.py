from app import build_cors_origins


def test_production_cors_only_allows_frontend_url():
    assert build_cors_origins(
        environment="production",
        frontend_url="https://cau-hc.com.ar/",
        configured_origins="",
    ) == ["https://cau-hc.com.ar"]


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
        frontend_url="https://cau-hc.com.ar",
        configured_origins="https://admin.example.com/, https://cau-hc.com.ar",
    ) == ["https://admin.example.com", "https://cau-hc.com.ar"]


def test_unknown_origin_receives_no_cors_header(client):
    response = client.get(
        "/api/health/public",
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_request_without_origin_receives_no_cors_header(client):
    response = client.get("/api/health/public")

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers
