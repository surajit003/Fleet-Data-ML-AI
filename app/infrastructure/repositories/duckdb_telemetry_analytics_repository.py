from datetime import date, datetime
from pathlib import Path

import duckdb

from app.domain.entities.telemetry_analytics_breakdown_row import (
    TelemetryAnalyticsBreakdownRow,
)
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

        with duckdb.connect(database=":memory:") as connection:
            row = connection.execute(
                self._summary_query(query),
                self._build_params(processed_path, query),
            ).fetchone()
            day_rows = connection.execute(
                self._records_by_day_query(query),
                self._build_params(processed_path, query),
            ).fetchall()
            vehicle_rows = connection.execute(
                self._records_by_vehicle_query(query),
                self._build_params(processed_path, query),
            ).fetchall()

        if row is None:
            raise RuntimeError("DuckDB did not return a summary row.")

        return TelemetryAnalyticsSummary(
            stored_filename=query.stored_filename,
            processed_path=processed_path,
            row_count=int(row[0]),
            distinct_vehicle_count=int(row[1]),
            first_recorded_at=self._to_iso_string(row[2]),
            last_recorded_at=self._to_iso_string(row[3]),
            records_by_day=tuple(
                TelemetryAnalyticsBreakdownRow(
                    label=str(day_row[0]),
                    count=int(day_row[1]),
                )
                for day_row in day_rows
            ),
            records_by_vehicle=tuple(
                TelemetryAnalyticsBreakdownRow(
                    label=str(vehicle_row[0]),
                    count=int(vehicle_row[1]),
                )
                for vehicle_row in vehicle_rows
            ),
        )

    def _to_iso_string(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat(sep="T")
        if isinstance(value, date):
            return value.isoformat()
        return str(value).replace(" ", "T", 1)

    def _build_params(
        self,
        processed_path: Path,
        query: TelemetryAnalyticsQuery,
    ) -> list[object]:
        params: list[object] = [str(processed_path)]
        if query.vehicle_registration:
            params.append(query.vehicle_registration)
        if query.start_recorded_at:
            params.append(query.start_recorded_at)
        if query.end_recorded_at:
            params.append(query.end_recorded_at)
        return params

    def _summary_query(self, query: TelemetryAnalyticsQuery) -> str:
        return f"""
            WITH telemetry AS (
                {self._filtered_telemetry_select(query)}
            )
            SELECT
                COUNT(*) AS row_count,
                COUNT(DISTINCT vehicle_registration) AS distinct_vehicle_count,
                MIN(TRY_CAST(recorded_at AS TIMESTAMP)) AS first_recorded_at,
                MAX(TRY_CAST(recorded_at AS TIMESTAMP)) AS last_recorded_at
            FROM telemetry
        """

    def _records_by_day_query(self, query: TelemetryAnalyticsQuery) -> str:
        return f"""
            WITH telemetry AS (
                {self._filtered_telemetry_select(query)}
            )
            SELECT
                CAST(TRY_CAST(recorded_at AS TIMESTAMP) AS DATE) AS recorded_day,
                COUNT(*) AS row_count
            FROM telemetry
            WHERE TRY_CAST(recorded_at AS TIMESTAMP) IS NOT NULL
            GROUP BY 1
            ORDER BY 1 ASC
        """

    def _records_by_vehicle_query(self, query: TelemetryAnalyticsQuery) -> str:
        return f"""
            WITH telemetry AS (
                {self._filtered_telemetry_select(query)}
            )
            SELECT
                COALESCE(
                    NULLIF(TRIM(vehicle_registration), ''),
                    'Not provided'
                ) AS vehicle_registration,
                COUNT(*) AS row_count
            FROM telemetry
            GROUP BY 1
            ORDER BY row_count DESC, vehicle_registration ASC
        """

    def _filtered_telemetry_select(self, query: TelemetryAnalyticsQuery) -> str:
        clauses = ["SELECT * FROM read_parquet(?) WHERE 1 = 1"]
        if query.vehicle_registration:
            clauses.append("AND vehicle_registration = ?")
        if query.start_recorded_at:
            clauses.append("AND TRY_CAST(recorded_at AS TIMESTAMP) >= TRY_CAST(? AS TIMESTAMP)")
        if query.end_recorded_at:
            clauses.append("AND TRY_CAST(recorded_at AS TIMESTAMP) <= TRY_CAST(? AS TIMESTAMP)")
        return " ".join(clauses)
