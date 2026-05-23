from abc import ABC, abstractmethod
from pathlib import Path


class TelemetryCuratedArtifactRepository(ABC):
    @abstractmethod
    def publish_curated_artifact(
        self,
        stored_filename: str,
        processed_path: Path,
    ) -> None:
        """Publish a curated artifact to the analytics storage layer."""
