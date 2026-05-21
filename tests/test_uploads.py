import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

TRACKZEE_HEADER = (
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
    "RFID-1,VIN-001,645,1,12345,678,1,trackzee-user,1280"
)


@pytest.fixture(autouse=True)
def clean_upload_dir() -> Iterator[None]:
    upload_dir = Path("data/raw/uploads")
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    yield
    if upload_dir.exists():
        shutil.rmtree(upload_dir)


def test_upload_telemetry_csv_returns_created() -> None:
    csv_bytes = f"{TRACKZEE_HEADER}\n{TRACKZEE_ROW}\n".encode()

    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("trakzee_export.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "trakzee_export.csv"
    assert body["content_type"] == "text/csv"
    assert body["size_bytes"] == len(csv_bytes)
    assert body["row_count"] == 1
    assert body["accepted_columns"][0] == "fetched_at"
    assert body["mapped_fields"]["Imeino"] == "device_imei"


def test_upload_rejects_non_csv_extension() -> None:
    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("trakzee_export.xlsx", b"not-csv", "application/vnd.ms-excel")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Only CSV uploads are supported."}


def test_upload_rejects_large_file() -> None:
    oversized = b"a" * ((2 * 1024 * 1024) + 1)

    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("trakzee_export.csv", oversized, "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "File exceeds the 2 MB upload limit."}


def test_upload_rejects_unexpected_headers() -> None:
    invalid_csv = b"one,two,three\n1,2,3\n"

    response = client.post(
        "/api/v1/uploads/telemetry",
        files={"file": ("trakzee_export.csv", invalid_csv, "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "CSV header does not match the required Trackzee export format."
    }
