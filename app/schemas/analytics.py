from pydantic import BaseModel


class TelemetryAnalyticsSummaryResponse(BaseModel):
    stored_filename: str
    processed_path: str
    row_count: int
    distinct_vehicle_count: int
    first_recorded_at: str | None
    last_recorded_at: str | None
    vehicle_registration: str | None = None
    start_recorded_at: str | None = None
    end_recorded_at: str | None = None
