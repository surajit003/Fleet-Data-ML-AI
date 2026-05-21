from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_page_renders_form() -> None:
    response = client.get("/upload")

    assert response.status_code == 200
    assert "Upload Trackzee CSV" in response.text
    assert 'type="file"' in response.text
    assert "/api/v1/uploads/telemetry" in response.text
