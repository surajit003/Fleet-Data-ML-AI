from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TelemetryAnalyticsQuery:
    stored_filename: str
    vehicle_registration: str | None = None
    start_recorded_at: str | None = None
    end_recorded_at: str | None = None
