import csv
import io
from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.telemetry_upload import TelemetryUpload
from app.domain.entities.telemetry_upload_payload import TelemetryUploadPayload
from app.domain.entities.upload_sanity_summary import (
    ColumnIssue,
    PreviewRow,
    UploadSanitySummary,
)
from app.domain.exceptions import InvalidTelemetryUploadError
from app.domain.repositories.upload_audit_repository import UploadAuditRepository
from app.domain.repositories.upload_storage_repository import UploadStorageRepository
from app.domain.telemetry_schema import (
    REQUIRED_VALUE_COLUMNS,
    TELEMETRY_PREVIEW_COLUMNS,
    TELEMETRY_TO_DOMAIN_FIELD_MAP,
    validate_telemetry_header,
)


@dataclass(frozen=True, slots=True)
class ValidatedTelemetryUpload:
    upload: TelemetryUpload
    sanity_summary: UploadSanitySummary


class TelemetryUploadService:
    def __init__(
        self,
        audit_repository: UploadAuditRepository,
        storage_repository: UploadStorageRepository,
        max_upload_size_bytes: int,
    ) -> None:
        self._audit_repository = audit_repository
        self._storage_repository = storage_repository
        self._max_upload_size_bytes = max_upload_size_bytes

    def upload_csv(self, payload: TelemetryUploadPayload) -> ValidatedTelemetryUpload:
        self._validate_filename(payload.filename)
        self._validate_size(payload.content)

        parsed_csv = self._parse_csv(payload.content)

        upload = self._storage_repository.save_telemetry_csv(
            original_filename=payload.filename,
            content_type=payload.content_type,
            content=payload.content,
            row_count=parsed_csv.row_count,
        )
        validated_upload = self._build_validated_upload(upload=upload, parsed_csv=parsed_csv)
        self._audit_repository.save_upload_audit(
            upload=upload,
            sanity_summary=validated_upload.sanity_summary,
        )
        return validated_upload

    def _build_validated_upload(
        self,
        upload: TelemetryUpload,
        parsed_csv: ParsedTelemetryCsv,
    ) -> ValidatedTelemetryUpload:
        return ValidatedTelemetryUpload(
            upload=upload,
            sanity_summary=UploadSanitySummary(
                preview_columns=parsed_csv.preview_columns,
                preview_rows=parsed_csv.preview_rows,
                warnings=parsed_csv.warnings,
                required_value_issues=parsed_csv.required_value_issues,
                unique_vehicle_count=parsed_csv.unique_vehicle_count,
                first_recorded_at=parsed_csv.first_recorded_at,
                last_recorded_at=parsed_csv.last_recorded_at,
            ),
        )

    def _validate_filename(self, filename: str) -> None:
        if not filename.lower().endswith(".csv"):
            raise InvalidTelemetryUploadError("Only CSV uploads are supported.")

    def _validate_size(self, content: bytes) -> None:
        if len(content) > self._max_upload_size_bytes:
            raise InvalidTelemetryUploadError("File exceeds the 2 MB upload limit.")

    def _parse_csv(self, content: bytes) -> ParsedTelemetryCsv:
        try:
            text_stream = io.StringIO(content.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise InvalidTelemetryUploadError("CSV file must be valid UTF-8 text.") from exc

        reader = csv.reader(text_stream)
        header = next(reader, None)
        if header is None:
            raise InvalidTelemetryUploadError("CSV file is empty.")
        validate_telemetry_header(header)

        preview_columns = tuple(
            column
            for column in TELEMETRY_PREVIEW_COLUMNS
            if column in TELEMETRY_TO_DOMAIN_FIELD_MAP
        )
        preview_rows: list[PreviewRow] = []
        required_value_counts = {column: 0 for column in REQUIRED_VALUE_COLUMNS}
        unique_vehicle_numbers: set[str] = set()
        recorded_at_values: list[datetime] = []
        warnings: list[str] = []
        warned_invalid_timestamp = False
        row_count = 0

        for row_number, row in enumerate(reader, start=2):
            if not any(cell.strip() for cell in row):
                continue

            if len(row) != len(header):
                raise InvalidTelemetryUploadError(
                    f"Row {row_number} has {len(row)} values, expected {len(header)}."
                )

            row_count += 1
            row_values = dict(zip(header, row, strict=True))

            for column in REQUIRED_VALUE_COLUMNS:
                if not row_values[column].strip():
                    required_value_counts[column] += 1

            vehicle_number = row_values.get("Vehicle_No", "").strip()
            if vehicle_number:
                unique_vehicle_numbers.add(vehicle_number)

            recorded_at = row_values.get("Datetime", "").strip()
            if recorded_at:
                try:
                    recorded_at_values.append(datetime.fromisoformat(recorded_at))
                except ValueError:
                    if not warned_invalid_timestamp:
                        warnings.append(
                            "Some Datetime values could not be parsed as ISO timestamps."
                        )
                        warned_invalid_timestamp = True

            if len(preview_rows) < 5:
                preview_rows.append(
                    PreviewRow(
                        row_number=row_number - 1,
                        values={column: row_values[column] for column in preview_columns},
                    )
                )

        if row_count == 0:
            warnings.append("The file contains the header row but no telemetry data rows.")

        required_value_issues = tuple(
            ColumnIssue(
                column=column,
                issue="Required values were blank.",
                affected_rows=count,
            )
            for column, count in sorted(required_value_counts.items())
            if count > 0
        )
        if required_value_issues:
            warnings.append(
                f"{len(required_value_issues)} required columns contain blank values."
            )

        first_recorded_at = None
        last_recorded_at = None
        if recorded_at_values:
            first_recorded_at = min(recorded_at_values).isoformat()
            last_recorded_at = max(recorded_at_values).isoformat()

        return ParsedTelemetryCsv(
            header=header,
            row_count=row_count,
            preview_columns=preview_columns,
            preview_rows=tuple(preview_rows),
            warnings=tuple(warnings),
            required_value_issues=required_value_issues,
            unique_vehicle_count=len(unique_vehicle_numbers),
            first_recorded_at=first_recorded_at,
            last_recorded_at=last_recorded_at,
        )


@dataclass(frozen=True, slots=True)
class ParsedTelemetryCsv:
    header: list[str]
    row_count: int
    preview_columns: tuple[str, ...]
    preview_rows: tuple[PreviewRow, ...]
    warnings: tuple[str, ...]
    required_value_issues: tuple[ColumnIssue, ...]
    unique_vehicle_count: int
    first_recorded_at: str | None
    last_recorded_at: str | None
