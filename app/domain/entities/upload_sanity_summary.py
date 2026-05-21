from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PreviewRow:
    row_number: int
    values: dict[str, str]


@dataclass(frozen=True, slots=True)
class ColumnIssue:
    column: str
    issue: str
    affected_rows: int


@dataclass(frozen=True, slots=True)
class UploadSanitySummary:
    preview_columns: tuple[str, ...]
    preview_rows: tuple[PreviewRow, ...]
    warnings: tuple[str, ...]
    required_value_issues: tuple[ColumnIssue, ...]
    unique_vehicle_count: int
    first_recorded_at: str | None
    last_recorded_at: str | None
