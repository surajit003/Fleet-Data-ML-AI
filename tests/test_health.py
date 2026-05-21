from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_expected_payload() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Fleet Data Platform",
        "version": "0.1.0",
        "environment": "local",
    }


def test_root_endpoint_returns_service_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "Fleet Data Platform",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
