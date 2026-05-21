import csv
import io
from dataclasses import dataclass

from app.domain.entities.telemetry_upload import TelemetryUpload
from app.domain.entities.telemetry_upload_payload import TelemetryUploadPayload
from app.domain.exceptions import InvalidTelemetryUploadError
from app.domain.repositories.upload_storage_repository import UploadStorageRepository
from app.domain.telemetry_schema import TRACKZEE_TO_DOMAIN_FIELD_MAP, validate_trackzee_header


@dataclass(frozen=True, slots=True)
class ValidatedTelemetryUpload:
    upload: TelemetryUpload
    mapped_fields: dict[str, str]


class TelemetryUploadService:
    def __init__(
        self,
        storage_repository: UploadStorageRepository,
        max_upload_size_bytes: int,
    ) -> None:
        self._storage_repository = storage_repository
        self._max_upload_size_bytes = max_upload_size_bytes

    def upload_csv(self, payload: TelemetryUploadPayload) -> ValidatedTelemetryUpload:
        self._validate_filename(payload.filename)
        self._validate_size(payload.content)

        header, row_count = self._parse_csv(payload.content)
        validate_trackzee_header(header)

        upload = self._storage_repository.save_telemetry_csv(
            original_filename=payload.filename,
            content_type=payload.content_type,
            content=payload.content,
            row_count=row_count,
        )
        return ValidatedTelemetryUpload(
            upload=upload,
            mapped_fields=TRACKZEE_TO_DOMAIN_FIELD_MAP,
        )

    def _validate_filename(self, filename: str) -> None:
        if not filename.lower().endswith(".csv"):
            raise InvalidTelemetryUploadError("Only CSV uploads are supported.")

    def _validate_size(self, content: bytes) -> None:
        if len(content) > self._max_upload_size_bytes:
            raise InvalidTelemetryUploadError("File exceeds the 2 MB upload limit.")

    def _parse_csv(self, content: bytes) -> tuple[list[str], int]:
        try:
            text_stream = io.StringIO(content.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise InvalidTelemetryUploadError("CSV file must be valid UTF-8 text.") from exc

        reader = csv.reader(text_stream)
        header = next(reader, None)
        if header is None:
            raise InvalidTelemetryUploadError("CSV file is empty.")

        row_count = sum(1 for row in reader if any(cell.strip() for cell in row))
        return header, row_count
