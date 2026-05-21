from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_page_renders_form() -> None:
    response = client.get("/upload")

    assert response.status_code == 200
    assert "Upload Telemetry Data" in response.text
    assert "Download sample CSV" in response.text
    assert "Required value" in response.text
    assert "Optional value" in response.text
    assert "Start with the sample" in response.text
    assert "Time and Source" in response.text
    assert "Vehicle Identity" in response.text
    assert "Device IMEI or hardware identifier." in response.text
    assert 'type="file"' in response.text
    assert '/static/upload/upload.css' in response.text
    assert '/static/upload/upload.js' in response.text
    assert 'apiPrefix: "/api/v1"' in response.text


def test_sample_download_returns_csv() -> None:
    response = client.get("/upload/sample")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"telemetry-sample.csv\"" == response.headers["content-disposition"]
    assert response.text.startswith("fetched_at,Imeino,Vehicle_No")
    assert "Demo Vehicle 0001" in response.text
