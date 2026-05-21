from abc import ABC, abstractmethod

from app.domain.entities.telemetry_analytics_query import TelemetryAnalyticsQuery
from app.domain.entities.telemetry_analytics_summary import TelemetryAnalyticsSummary


class TelemetryAnalyticsRepository(ABC):
    @abstractmethod
    def summarize_curated_upload(
        self,
        query: TelemetryAnalyticsQuery,
    ) -> TelemetryAnalyticsSummary:
        """Return a DuckDB-backed summary for a curated telemetry upload."""
