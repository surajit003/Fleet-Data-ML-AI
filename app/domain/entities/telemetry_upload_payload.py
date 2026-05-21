from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TelemetryUploadPayload:
    filename: str
    content_type: str
    content: bytes
