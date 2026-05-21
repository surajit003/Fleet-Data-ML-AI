from datetime import date, datetime
from pathlib import Path

import duckdb

from app.domain.entities.telemetry_analytics_query import TelemetryAnalyticsQuery
from app.domain.entities.telemetry_analytics_summary import TelemetryAnalyticsSummary
from app.domain.repositories.telemetry_analytics_repository import (
    TelemetryAnalyticsRepository,
)


class DuckDBTelemetryAnalyticsRepository(TelemetryAnalyticsRepository):
    def __init__(self, processed_storage_dir: Path) -> None:
        self._processed_storage_dir = processed_storage_dir

    def summarize_curated_upload(
        self,
        query: TelemetryAnalyticsQuery,
    ) -> TelemetryAnalyticsSummary:
        processed_path = (
            self._processed_storage_dir
            / f"curated_{Path(query.stored_filename).stem}.parquet"
        )
        if not processed_path.exists():
            raise FileNotFoundError(query.stored_filename)

        clauses = ["SELECT * FROM read_parquet(?) WHERE 1 = 1"]
        params: list[object] = [str(processed_path)]
        if query.vehicle_registration:
            clauses.append("AND vehicle_registration = ?")
            params.append(query.vehicle_registration)
        if query.start_recorded_at:
            clauses.append("AND TRY_CAST(recorded_at AS TIMESTAMP) >= TRY_CAST(? AS TIMESTAMP)")
            params.append(query.start_recorded_at)
        if query.end_recorded_at:
            clauses.append("AND TRY_CAST(recorded_at AS TIMESTAMP) <= TRY_CAST(? AS TIMESTAMP)")
            params.append(query.end_recorded_at)
        analytics_query = f"""
            WITH telemetry AS (
                {' '.join(clauses)}
            )
            SELECT
                COUNT(*) AS row_count,
                COUNT(DISTINCT vehicle_registration) AS distinct_vehicle_count,
                MIN(TRY_CAST(recorded_at AS TIMESTAMP)) AS first_recorded_at,
                MAX(TRY_CAST(recorded_at AS TIMESTAMP)) AS last_recorded_at
            FROM telemetry
        """
        with duckdb.connect(database=":memory:") as connection:
            row = connection.execute(analytics_query, params).fetchone()

        if row is None:
            raise RuntimeError("DuckDB did not return a summary row.")

        return TelemetryAnalyticsSummary(
            stored_filename=query.stored_filename,
            processed_path=processed_path,
            row_count=int(row[0]),
            distinct_vehicle_count=int(row[1]),
            first_recorded_at=self._to_iso_string(row[2]),
            last_recorded_at=self._to_iso_string(row[3]),
        )

    def _to_iso_string(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat(sep="T")
        if isinstance(value, date):
            return value.isoformat()
        return str(value).replace(" ", "T", 1)
