from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import register_error_handlers


def test_unknown_error_is_500_with_request_id_and_no_detail_leak():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError("postgresql://user:secret@example/db")

    with TestClient(app) as client:
        response = client.get("/boom", headers={"X-Request-ID": "rid-500"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert response.headers["X-Request-ID"] == "rid-500"
    assert "secret" not in response.text
