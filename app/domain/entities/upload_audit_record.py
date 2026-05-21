from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UploadAuditRecord:
    status: str
    stored_filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    row_count: int
    unique_vehicle_count: int
    warning_count: int
    warnings: tuple[str, ...]
    first_recorded_at: str | None
    last_recorded_at: str | None
    processed_path: str | None
    transformed_row_count: int | None
    duplicate_row_count: int | None
    transformed_at: str | None
    created_at: str
