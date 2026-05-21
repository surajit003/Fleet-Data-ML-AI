from pydantic import BaseModel


class TelemetryUploadResponse(BaseModel):
    filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    row_count: int
    accepted_columns: list[str]
    mapped_fields: dict[str, str]
