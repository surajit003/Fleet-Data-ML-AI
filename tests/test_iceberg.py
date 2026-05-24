from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from app.application.services.telemetry_analytics_service import (
    TelemetryAnalyticsService,
)
from app.core.config import Settings
from app.domain.entities.telemetry_analytics_query import TelemetryAnalyticsQuery
from app.infrastructure.iceberg.bootstrap import bootstrap_iceberg_table
from app.infrastructure.iceberg.catalog import (
    load_iceberg_catalog,
    resolve_iceberg_identifier,
)
from app.infrastructure.repositories.duckdb_telemetry_analytics_repository import (
    DuckDBTelemetryAnalyticsRepository,
)
from app.infrastructure.repositories.local_telemetry_curated_artifact_repository import (
    LocalTelemetryCuratedArtifactRepository,
)


def _build_settings(tmp_path: Path) -> Settings:
    metadata_dir = tmp_path / "metadata"
    processed_dir = tmp_path / "processed"
    iceberg_dir = tmp_path / "iceberg"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    iceberg_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        storage_backend="local",
        analytics_backend="duckdb",
        upload_storage_dir=tmp_path / "raw",
        processed_storage_dir=processed_dir,
        upload_metadata_db_path=metadata_dir / "uploads.db",
        iceberg_catalog_type="sql",
        iceberg_catalog_uri=f"sqlite:///{metadata_dir / 'iceberg_catalog.db'}",
        iceberg_warehouse_uri=f"file://{iceberg_dir}",
        iceberg_namespace="telemetry",
        iceberg_table_name="curated_events",
    )


def _build_curated_row() -> dict[str, object]:
    timestamp = datetime(2026, 5, 21, 10, 2, 5)
    return {
        "fetched_at": timestamp,
        "device_imei": 353201358287644,
        "vehicle_registration": "DEMO-0001",
        "vehicle_name": "Demo Vehicle 0001",
        "company_name": "Demo Fleet",
        "branch_name": "Nairobi",
        "vehicle_type": "Truck",
        "device_model": "FMB920",
        "vehicle_status": "STOP",
        "power_state": "ON",
        "ignition_state": "OFF",
        "gps_state": "ON",
        "speed_kph": 0,
        "heading_angle": 97,
        "course": 97,
        "odometer": 16514271,
        "can_odometer": 16514271,
        "latitude": -15.3960833,
        "longitude": 28.2775016,
        "location_text": "Nsato Road, Emmasdale",
        "point_of_interest": "",
        "gps_actual_time": timestamp,
        "recorded_at": timestamp,
        "temperature": 24,
        "external_voltage": 12.4,
        "battery_percentage": 90,
        "satellite_count": 12,
        "gps_hdop": 0.9,
        "fuel_level": 50,
        "ac_state": "OFF",
        "sos_state": "OFF",
        "immobilize_state": "OFF",
        "door_1_state": "CLOSED",
        "door_2_state": "CLOSED",
        "door_3_state": "CLOSED",
        "door_4_state": "CLOSED",
        "electronic_lock_state": "OFF",
        "driver_first_name": "John",
        "driver_middle_name": "",
        "driver_last_name": "Doe",
        "driver_ibutton_rfid": "RFID-1",
        "vin": "VIN-001",
        "mobile_country_code": 645,
        "mobile_network_code": 1,
        "cell_id": 12345,
        "location_area_code": 678,
        "heartbeat": 1,
        "source_username": "demo-user",
        "altitude": 1280,
    }


def test_iceberg_append_is_idempotent_and_queryable(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    bootstrap_iceberg_table(settings)

    processed_dir = settings.processed_storage_dir
    processed_dir.mkdir(parents=True, exist_ok=True)
    processed_path = processed_dir / "curated_telemetry_upload.parquet"
    pq.write_table(
        pa.Table.from_pylist([_build_curated_row()]),
        processed_path,
    )  # type: ignore[no-untyped-call]

    repository = LocalTelemetryCuratedArtifactRepository(settings=settings)
    repository.publish_curated_artifact("telemetry_upload.csv", processed_path)
    repository.publish_curated_artifact("telemetry_upload.csv", processed_path)

    table = load_iceberg_catalog(settings).load_table(resolve_iceberg_identifier(settings))
    assert table.scan().count() == 1

    analytics_service = TelemetryAnalyticsService(
        repository=DuckDBTelemetryAnalyticsRepository(settings=settings)
    )
    summary = analytics_service.summarize_curated_upload(
        TelemetryAnalyticsQuery(stored_filename="telemetry_upload.csv")
    )

    assert summary.row_count == 1
    assert summary.distinct_vehicle_count == 1
    assert summary.first_recorded_at == "2026-05-21T10:02:05"
    assert summary.last_recorded_at == "2026-05-21T10:02:05"
    assert [(row.label, row.count) for row in summary.records_by_day] == [
        ("2026-05-21", 1)
    ]
    assert [(row.label, row.count) for row in summary.records_by_vehicle] == [
        ("DEMO-0001", 1)
    ]
