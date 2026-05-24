import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.infrastructure.iceberg.catalog import (
    load_gcp_iceberg_catalog,
    load_local_iceberg_catalog,
)
from app.main import app

client = TestClient(app)

REQUIRED_TELEMETRY_HEADER = (
    "fetched_at,Imeino,Vehicle_No,Vehicle_Name,Company,Branch,Vehicletype,DeviceModel,"
    "Status,Power,IGN,GPS,Speed,Angle,course,Odometer,can_odometer,Latitude,Longitude,"
    "Location,POI,GPSActualTime,Datetime,Temperature,ExternalVolt,battery_percentage,"
    "satellite_count,gps_hdop,Fuel,AC,SOS,Immobilize_State,Door1,Door2,Door3,Door4,"
    "elock,Driver_First_Name,Driver_Middle_Name,Driver_Last_Name,Ibutton/RFID,Vin,mcc,"
    "mnc,cellid,lac,heartbeat,username,Altitude"
)

TRACKZEE_ROW = (
    "2026-04-29T16:49:52,353201358287644,BCA 4676 (COMPANY),BCA 4676,ZM Pepsi,"
    "Route Truck,Minitruck,FMB920,STOP,ON,OFF,ON,0,97,97,16514271,0,-15.3960833,"
    "28.2775016,\"Nsato Road, Emmasdale\",,2026-04-29T16:49:50,2026-04-29T16:49:50,"
    "24,12.4,90,12,0.9,50,OFF,OFF,OFF,CLOSED,CLOSED,CLOSED,CLOSED,OFF,John,,Doe,"
    "RFID-1,VIN-001,645,1,12345,678,1,demo-user,1280"
)


@pytest.fixture(autouse=True)
def clean_upload_dir() -> Iterator[None]:
    load_local_iceberg_catalog.cache_clear()
    load_gcp_iceberg_catalog.cache_clear()
    upload_dir = Path("data/raw/uploads")
    processed_dir = Path("data/processed/telemetry")
    metadata_dir = Path("data/metadata")
    iceberg_dir = Path("data/iceberg")
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    if processed_dir.exists():
        shutil.rmtree(processed_dir)
    if metadata_dir.exists():
        shutil.rmtree(metadata_dir)
    if iceberg_dir.exists():
        shutil.rmtree(iceberg_dir)
    load_local_iceberg_catalog.cache_clear()
    load_gcp_iceberg_catalog.cache_clear()
    yield
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    if processed_dir.exists():
        shutil.rmtree(processed_dir)
    if metadata_dir.exists():
        shutil.rmtree(metadata_dir)
    if iceberg_dir.exists():
        shutil.rmtree(iceberg_dir)


def test_upload_telemetry_csv_returns_created() -> None:
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n".encode()

    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "telemetry_upload.csv"
    assert body["status"] == "validated"
    assert body["content_type"] == "text/csv"
    assert body["size_bytes"] == len(csv_bytes)
    assert body["row_count"] == 1
    assert body["sanity_summary"]["preview_columns"][0] == "Datetime"
    assert body["sanity_summary"]["preview_rows"][0]["values"]["Vehicle_No"] == "BCA 4676 (COMPANY)"
    assert body["sanity_summary"]["unique_vehicle_count"] == 1
    assert body["sanity_summary"]["warnings"] == []


def test_upload_telemetry_csv_requires_api_key_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test-secret")
    get_settings.cache_clear()

    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n".encode()
    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."

    authorized_response = client.post(
        "/api/v1/uploads/telemetry",
        headers={"X-API-Key": "test-secret"},
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert authorized_response.status_code == 201
    assert authorized_response.json()["status"] == "validated"

    monkeypatch.delenv("API_KEY", raising=False)
    get_settings.cache_clear()


def test_upload_telemetry_csv_rejects_before_body_parsing_when_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "test-secret")
    get_settings.cache_clear()

    response = client.request(
        "POST",
        "/api/v1/uploads/telemetry",
        content=b"not-a-multipart-body",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."

    monkeypatch.delenv("API_KEY", raising=False)
    get_settings.cache_clear()


def test_upload_reports_blank_required_values() -> None:
    invalid_required_row = TRACKZEE_ROW.replace("BCA 4676 (COMPANY)", "", 1)
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{invalid_required_row}\n".encode()

    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert "1 required columns contain blank values." in body["sanity_summary"]["warnings"]
    assert body["sanity_summary"]["required_value_issues"] == [
        {
            "column": "Vehicle_No",
            "issue": "Required values were blank.",
            "affected_rows": 1,
        }
    ]


def test_upload_history_returns_recent_uploads() -> None:
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert upload_response.status_code == 201

    history_response = client.get("/api/v1/uploads/history")

    assert history_response.status_code == 200
    body = history_response.json()
    assert len(body["uploads"]) == 1
    assert body["uploads"][0]["status"] == "validated"
    assert body["uploads"][0]["original_filename"] == "telemetry_upload.csv"
    assert body["uploads"][0]["row_count"] == 1
    assert body["uploads"][0]["warning_count"] == 0


def test_upload_detail_returns_saved_sanity_summary() -> None:
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert upload_response.status_code == 201
    stored_filename = upload_response.json()["stored_filename"]

    detail_response = client.get(f"/api/v1/uploads/history/{stored_filename}")

    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["upload"]["status"] == "validated"
    assert body["upload"]["stored_filename"] == stored_filename
    assert body["sanity_summary"]["preview_rows"][0]["values"]["Vehicle_Name"] == "BCA 4676"
    assert body["sanity_summary"]["warnings"] == []


def test_upload_history_marks_warning_status() -> None:
    invalid_required_row = TRACKZEE_ROW.replace("BCA 4676 (COMPANY)", "", 1)
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{invalid_required_row}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert upload_response.status_code == 201

    history_response = client.get("/api/v1/uploads/history")

    assert history_response.status_code == 200
    body = history_response.json()
    assert body["uploads"][0]["status"] == "validated_with_warnings"


def test_prepare_transform_updates_upload_status() -> None:
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert upload_response.status_code == 201
    stored_filename = upload_response.json()["stored_filename"]

    prepare_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/prepare-transform"
    )

    assert prepare_response.status_code == 200
    body = prepare_response.json()
    assert body["upload"]["status"] == "ready_for_transform"

    history_response = client.get("/api/v1/uploads/history")
    assert history_response.status_code == 200
    assert history_response.json()["uploads"][0]["status"] == "ready_for_transform"


def test_run_transform_updates_status_and_artifact_metadata() -> None:
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert upload_response.status_code == 201
    stored_filename = upload_response.json()["stored_filename"]

    prepare_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/prepare-transform"
    )
    assert prepare_response.status_code == 200

    transform_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/run-transform"
    )

    assert transform_response.status_code == 200
    body = transform_response.json()
    assert body["upload"]["status"] == "transformed"
    assert body["upload"]["transformed_row_count"] == 1
    assert body["upload"]["duplicate_row_count"] == 0
    assert body["upload"]["processed_path"] is not None
    assert body["upload"]["processed_path"].endswith(
        f"curated_{Path(stored_filename).stem}.parquet"
    )


def test_run_transform_skips_duplicate_rows() -> None:
    duplicate_csv = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n{TRACKZEE_ROW}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", duplicate_csv, "text/csv")},
    )

    assert upload_response.status_code == 201
    stored_filename = upload_response.json()["stored_filename"]

    prepare_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/prepare-transform"
    )
    assert prepare_response.status_code == 200

    transform_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/run-transform"
    )

    assert transform_response.status_code == 200
    body = transform_response.json()
    assert body["upload"]["transformed_row_count"] == 1
    assert body["upload"]["duplicate_row_count"] == 1
    assert body["duplicate_diagnostics"] == [
        {
            "row_number": 3,
            "duplicate_of_row_number": 2,
            "duplicate_key": "353201358287644 | 2026-04-29T16:49:50",
            "device_imei": "353201358287644",
            "vehicle_registration": "BCA 4676 (COMPANY)",
            "recorded_at": "2026-04-29T16:49:50",
            "reason": "Matched a previously seen telemetry event using device and timestamp.",
        }
    ]

    detail_response = client.get(f"/api/v1/uploads/history/{stored_filename}")
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["duplicate_diagnostics"] == body["duplicate_diagnostics"]


def test_transform_uses_default_exact_event_duplicate_strategy() -> None:
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n{TRACKZEE_ROW}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert upload_response.status_code == 201
    stored_filename = upload_response.json()["stored_filename"]

    prepare_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/prepare-transform"
    )
    assert prepare_response.status_code == 200

    transform_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/run-transform"
    )

    assert transform_response.status_code == 200
    body = transform_response.json()
    assert body["upload"]["duplicate_row_count"] == 1
    assert (
        body["duplicate_diagnostics"][0]["reason"]
        == "Matched a previously seen telemetry event using device and timestamp."
    )


def test_processed_artifact_download_returns_curated_file() -> None:
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert upload_response.status_code == 201
    stored_filename = upload_response.json()["stored_filename"]

    prepare_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/prepare-transform"
    )
    assert prepare_response.status_code == 200

    transform_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/run-transform"
    )
    assert transform_response.status_code == 200

    artifact_response = client.get(
        f"/api/v1/uploads/history/{stored_filename}/processed-artifact"
    )

    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"].startswith("application/octet-stream")
    assert artifact_response.headers["content-disposition"].endswith(".parquet\"")


def test_duckdb_summary_returns_basic_metrics() -> None:
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert upload_response.status_code == 201
    stored_filename = upload_response.json()["stored_filename"]

    prepare_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/prepare-transform"
    )
    assert prepare_response.status_code == 200

    transform_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/run-transform"
    )
    assert transform_response.status_code == 200

    analytics_response = client.get(
        f"/api/v1/analytics/telemetry/{stored_filename}/summary"
    )

    assert analytics_response.status_code == 200
    body = analytics_response.json()
    assert body["stored_filename"] == stored_filename
    assert body["row_count"] == 1
    assert body["distinct_vehicle_count"] == 1
    assert body["first_recorded_at"] == "2026-04-29T16:49:50"
    assert body["last_recorded_at"] == "2026-04-29T16:49:50"
    assert body["records_by_day"] == [{"label": "2026-04-29", "count": 1}]
    assert body["records_by_vehicle"] == [
        {"label": "BCA 4676 (COMPANY)", "count": 1}
    ]
    assert body["vehicle_registration"] is None
    assert body["start_recorded_at"] is None
    assert body["end_recorded_at"] is None


def test_duckdb_summary_accepts_filters() -> None:
    csv_bytes = f"{REQUIRED_TELEMETRY_HEADER}\n{TRACKZEE_ROW}\n".encode()

    upload_response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", csv_bytes, "text/csv")},
    )

    assert upload_response.status_code == 201
    stored_filename = upload_response.json()["stored_filename"]

    prepare_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/prepare-transform"
    )
    assert prepare_response.status_code == 200

    transform_response = client.post(
        f"/api/v1/uploads/history/{stored_filename}/run-transform"
    )
    assert transform_response.status_code == 200

    analytics_response = client.get(
        f"/api/v1/analytics/telemetry/{stored_filename}/summary",
        params={"vehicle_registration": "BCA 4676 (COMPANY)"},
    )

    assert analytics_response.status_code == 200
    body = analytics_response.json()
    assert body["row_count"] == 1
    assert body["distinct_vehicle_count"] == 1
    assert body["vehicle_registration"] == "BCA 4676 (COMPANY)"
    assert body["records_by_vehicle"] == [
        {"label": "BCA 4676 (COMPANY)", "count": 1}
    ]


def test_duckdb_summary_rejects_missing_file() -> None:
    response = client.get("/api/v1/analytics/telemetry/missing.csv/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "Curated upload not found."


def test_upload_rejects_non_csv_extension() -> None:
    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.xlsx", b"not-csv", "application/vnd.ms-excel")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Only CSV uploads are supported."}


def test_upload_rejects_large_file() -> None:
    oversized = b"a" * ((2 * 1024 * 1024) + 1)

    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", oversized, "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "File exceeds the 2 MB upload limit."}


def test_upload_rejects_unexpected_headers() -> None:
    invalid_csv = b"one,two,three\n1,2,3\n"

    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("telemetry_upload.csv", invalid_csv, "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "CSV header does not match the required telemetry ingestion format."
    }
