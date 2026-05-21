from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TelemetryUpload:
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    row_count: int
    stored_path: Path
