from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.domain.entities.telemetry_upload import TelemetryUpload


class LocalUploadStorageRepository:
    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir

    def save_telemetry_csv(
        self,
        original_filename: str,
        content_type: str,
        content: bytes,
        row_count: int,
    ) -> TelemetryUpload:
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(original_filename).suffix.lower()
        stored_filename = (
            f"telemetry_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex}{suffix}"
        )
        stored_path = self._storage_dir / stored_filename
        stored_path.write_bytes(content)

        return TelemetryUpload(
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=len(content),
            row_count=row_count,
            stored_path=stored_path,
        )
