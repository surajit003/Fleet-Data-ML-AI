from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from google.cloud.storage import Client as StorageClient

from app.domain.entities.telemetry_upload import TelemetryUpload


class GcsUploadStorageRepository:
    def __init__(
        self,
        storage_dir: Path,
        project_id: str,
        raw_bucket_name: str,
    ) -> None:
        self._storage_dir = storage_dir
        self._project_id = project_id
        self._raw_bucket_name = raw_bucket_name

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
        local_path = self._storage_dir / stored_filename
        local_path.write_bytes(content)

        self._upload_to_gcs(stored_filename=stored_filename, content=content)

        return TelemetryUpload(
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=len(content),
            row_count=row_count,
            stored_path=local_path,
        )

    def _upload_to_gcs(self, stored_filename: str, content: bytes) -> None:
        client = StorageClient(project=self._project_id)
        bucket = client.bucket(self._raw_bucket_name)
        blob = bucket.blob(f"raw/{stored_filename}")
        blob.upload_from_string(content, content_type="text/csv")
