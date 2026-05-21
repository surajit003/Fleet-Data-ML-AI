from app.core.config import Settings
from app.domain.entities.health_status import HealthStatus


class StaticHealthRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_health_status(self) -> HealthStatus:
        return HealthStatus(
            status="ok",
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.environment,
        )
