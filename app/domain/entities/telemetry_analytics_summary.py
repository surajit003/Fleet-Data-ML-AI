from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TelemetryAnalyticsSummary:
    stored_filename: str
    processed_path: Path
    row_count: int
    distinct_vehicle_count: int
    first_recorded_at: str | None
    last_recorded_at: str | None
