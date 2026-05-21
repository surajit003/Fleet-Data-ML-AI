class DomainError(Exception):
    """Base domain exception."""


class InvalidTelemetryUploadError(DomainError):
    """Raised when a telemetry upload fails validation."""
