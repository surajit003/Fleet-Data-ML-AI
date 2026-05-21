from typing import Protocol

from app.domain.entities.health_status import HealthStatus


class HealthRepository(Protocol):
    def get_health_status(self) -> HealthStatus: ...
