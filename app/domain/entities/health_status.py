from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthStatus:
    status: str
    service: str
    version: str
    environment: str
