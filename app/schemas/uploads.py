from pydantic import BaseModel


class DuplicateRowDiagnosticResponse(BaseModel):
    row_number: int
    duplicate_of_row_number: int
    duplicate_key: str
    device_imei: str
    vehicle_registration: str
    recorded_at: str
    reason: str


class UploadAuditRecordResponse(BaseModel):
    status: str
    stored_filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    row_count: int
    unique_vehicle_count: int
    warning_count: int
    warnings: list[str]
    first_recorded_at: str | None
    last_recorded_at: str | None
    processed_path: str | None
    transformed_row_count: int | None
    duplicate_row_count: int | None
    transformed_at: str | None
    created_at: str


class TelemetryPreviewRow(BaseModel):
    row_number: int
    values: dict[str, str]


class TelemetryColumnIssue(BaseModel):
    column: str
    issue: str
    affected_rows: int


class TelemetrySanitySummary(BaseModel):
    preview_columns: list[str]
    preview_rows: list[TelemetryPreviewRow]
    warnings: list[str]
    required_value_issues: list[TelemetryColumnIssue]
    unique_vehicle_count: int
    first_recorded_at: str | None
    last_recorded_at: str | None


class TelemetryUploadResponse(BaseModel):
    status: str
    filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    row_count: int
    sanity_summary: TelemetrySanitySummary


class UploadHistoryResponse(BaseModel):
    uploads: list[UploadAuditRecordResponse]


class UploadDetailResponse(BaseModel):
    upload: UploadAuditRecordResponse
    sanity_summary: TelemetrySanitySummary
    duplicate_diagnostics: list[DuplicateRowDiagnosticResponse]
