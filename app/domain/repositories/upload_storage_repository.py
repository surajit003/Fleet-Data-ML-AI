from typing import Protocol

from app.domain.entities.telemetry_upload import TelemetryUpload


class UploadStorageRepository(Protocol):
    def save_telemetry_csv(
        self,
        original_filename: str,
        content_type: str,
        content: bytes,
        row_count: int,
    ) -> TelemetryUpload: ...
