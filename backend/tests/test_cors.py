from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_cors_allows_local_vite_origin():
    app = create_app(Settings(_env_file=None, database_url=None))
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"Origin": "http://127.0.0.1:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_cors_does_not_echo_unlisted_origin():
    app = create_app(Settings(_env_file=None, database_url=None))
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_config_is_operator_controlled():
    app = create_app(
        Settings(
            _env_file=None,
            database_url=None,
            cors_allow_origins="https://frontend.example",
        )
    )
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"Origin": "https://frontend.example"})
    assert response.headers["access-control-allow-origin"] == "https://frontend.example"
