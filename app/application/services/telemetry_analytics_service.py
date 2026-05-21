from app.domain.entities.telemetry_analytics_query import TelemetryAnalyticsQuery
from app.domain.entities.telemetry_analytics_summary import TelemetryAnalyticsSummary
from app.domain.repositories.telemetry_analytics_repository import (
    TelemetryAnalyticsRepository,
)


class TelemetryAnalyticsService:
    def __init__(self, repository: TelemetryAnalyticsRepository) -> None:
        self._repository = repository

    def summarize_curated_upload(
        self,
        query: TelemetryAnalyticsQuery,
    ) -> TelemetryAnalyticsSummary:
        return self._repository.summarize_curated_upload(query)
