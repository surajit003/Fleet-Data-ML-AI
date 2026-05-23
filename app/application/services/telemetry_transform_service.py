import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import duckdb

from app.domain.entities.duplicate_row_diagnostic import DuplicateRowDiagnostic
from app.domain.repositories.telemetry_curated_artifact_repository import (
    TelemetryCuratedArtifactRepository,
)
from app.domain.telemetry_schema import REQUIRED_TELEMETRY_COLUMNS, TELEMETRY_TO_DOMAIN_FIELD_MAP

DuplicateStrategy = Literal["exact_event", "event_with_position"]


@dataclass(frozen=True, slots=True)
class TransformResult:
    processed_path: Path
    row_count: int
    duplicate_row_count: int
    duplicate_diagnostics: tuple[DuplicateRowDiagnostic, ...]


class TelemetryTransformService:
    def __init__(
        self,
        raw_storage_dir: Path,
        processed_storage_dir: Path,
        duplicate_strategy: DuplicateStrategy = "exact_event",
        curated_artifact_repository: TelemetryCuratedArtifactRepository | None = None,
    ) -> None:
        self._raw_storage_dir = raw_storage_dir
        self._processed_storage_dir = processed_storage_dir
        self._duplicate_strategy = duplicate_strategy
        self._curated_artifact_repository = curated_artifact_repository

    def transform_upload(self, stored_filename: str) -> TransformResult:
        source_path = self._raw_storage_dir / stored_filename
        if not source_path.exists():
            raise FileNotFoundError(stored_filename)

        self._processed_storage_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(stored_filename).stem
        temp_csv_path = self._processed_storage_dir / f"curated_{base_name}.csv"
        processed_path = self._processed_storage_dir / f"curated_{base_name}.parquet"
        row_count = 0
        duplicate_row_count = 0
        duplicate_diagnostics: list[DuplicateRowDiagnostic] = []
        seen_rows: dict[tuple[str, ...], int] = {}

        with source_path.open("r", encoding="utf-8-sig", newline="") as source_file:
            reader = csv.DictReader(source_file)
            with temp_csv_path.open("w", encoding="utf-8", newline="") as target_file:
                writer = csv.DictWriter(
                    target_file,
                    fieldnames=list(TELEMETRY_TO_DOMAIN_FIELD_MAP.values()),
                )
                writer.writeheader()
                for row_number, row in enumerate(reader, start=2):
                    if not any((value or "").strip() for value in row.values()):
                        continue
                    normalized_row = {
                        TELEMETRY_TO_DOMAIN_FIELD_MAP[column]: row[column]
                        for column in REQUIRED_TELEMETRY_COLUMNS
                    }
                    duplicate_key = self._build_duplicate_key(normalized_row)
                    if duplicate_key in seen_rows:
                        duplicate_row_count += 1
                        if len(duplicate_diagnostics) < 5:
                            duplicate_diagnostics.append(
                                DuplicateRowDiagnostic(
                                    row_number=row_number,
                                    duplicate_of_row_number=seen_rows[duplicate_key],
                                    duplicate_key=" | ".join(duplicate_key),
                                    device_imei=normalized_row["device_imei"],
                                    vehicle_registration=normalized_row[
                                        "vehicle_registration"
                                    ],
                                    recorded_at=normalized_row["recorded_at"],
                                    reason=self._duplicate_reason(),
                                )
                            )
                        continue
                    seen_rows[duplicate_key] = row_number
                    writer.writerow(
                        normalized_row
                    )
                    row_count += 1

        with duckdb.connect(database=":memory:") as connection:
            processed_path_sql = self._sql_string_literal(processed_path)
            connection.execute(
                f"COPY (SELECT * FROM read_csv_auto(?)) TO {processed_path_sql} "
                "(FORMAT PARQUET)",
                [str(temp_csv_path)],
            )

        if temp_csv_path.exists():
            temp_csv_path.unlink()

        if self._curated_artifact_repository is not None:
            self._curated_artifact_repository.publish_curated_artifact(
                stored_filename=stored_filename,
                processed_path=processed_path,
            )

        return TransformResult(
            processed_path=processed_path,
            row_count=row_count,
            duplicate_row_count=duplicate_row_count,
            duplicate_diagnostics=tuple(duplicate_diagnostics),
        )

    def _build_duplicate_key(self, row: dict[str, str]) -> tuple[str, ...]:
        device_identifier = (row["device_imei"] or "").strip()
        if not device_identifier:
            device_identifier = (row["vehicle_registration"] or "").strip()
        recorded_at = (row["recorded_at"] or "").strip()
        if self._duplicate_strategy == "event_with_position":
            latitude = (row["latitude"] or "").strip()
            longitude = (row["longitude"] or "").strip()
            return (device_identifier, recorded_at, latitude, longitude)
        return (device_identifier, recorded_at)

    def _duplicate_reason(self) -> str:
        if self._duplicate_strategy == "event_with_position":
            return (
                "Matched a previously seen telemetry event using device, timestamp, "
                "and position."
            )
        return "Matched a previously seen telemetry event using device and timestamp."

    def _sql_string_literal(self, path: Path) -> str:
        escaped_path = str(path).replace("'", "''")
        return f"'{escaped_path}'"
