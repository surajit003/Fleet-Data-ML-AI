from pydantic import BaseModel


class TelemetryAnalyticsBreakdownRowResponse(BaseModel):
    label: str
    count: int


class TelemetryAnalyticsSummaryResponse(BaseModel):
    stored_filename: str
    processed_path: str
    row_count: int
    distinct_vehicle_count: int
    first_recorded_at: str | None
    last_recorded_at: str | None
    records_by_day: list[TelemetryAnalyticsBreakdownRowResponse]
    records_by_vehicle: list[TelemetryAnalyticsBreakdownRowResponse]
    vehicle_registration: str | None = None
    start_recorded_at: str | None = None
    end_recorded_at: str | None = None
