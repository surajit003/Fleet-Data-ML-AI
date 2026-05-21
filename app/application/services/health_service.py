from app.domain.entities.health_status import HealthStatus
from app.domain.repositories.health_repository import HealthRepository


class HealthService:
    def __init__(self, repository: HealthRepository) -> None:
        self._repository = repository

    def get_health_status(self) -> HealthStatus:
        return self._repository.get_health_status()
