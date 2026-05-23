from pathlib import Path

from app.domain.repositories.telemetry_curated_artifact_repository import (
    TelemetryCuratedArtifactRepository,
)


class LocalTelemetryCuratedArtifactRepository(TelemetryCuratedArtifactRepository):
    def publish_curated_artifact(
        self,
        stored_filename: str,
        processed_path: Path,
    ) -> None:
        _ = stored_filename
        _ = processed_path
