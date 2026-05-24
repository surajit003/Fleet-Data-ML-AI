from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
from pyiceberg.expressions import (
    And,
    BooleanExpression,
    EqualTo,
    GreaterThanOrEqual,
    LessThanOrEqual,
)

from app.core.config import Settings
from app.domain.entities.telemetry_analytics_breakdown_row import (
    TelemetryAnalyticsBreakdownRow,
)
from app.domain.entities.telemetry_analytics_query import TelemetryAnalyticsQuery
from app.domain.entities.telemetry_analytics_summary import TelemetryAnalyticsSummary
from app.domain.repositories.telemetry_analytics_repository import (
    TelemetryAnalyticsRepository,
)
from app.infrastructure.iceberg.catalog import load_iceberg_catalog, resolve_iceberg_identifier


class DuckDBTelemetryAnalyticsRepository(TelemetryAnalyticsRepository):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def summarize_curated_upload(
        self,
        query: TelemetryAnalyticsQuery,
    ) -> TelemetryAnalyticsSummary:
        table = load_iceberg_catalog(self._settings).load_table(
            resolve_iceberg_identifier(self._settings)
        )
        row_filter = self._build_row_filter(query)
        arrow_table = table.scan(row_filter=row_filter).to_arrow()

        with duckdb.connect(database=":memory:") as connection:
            connection.register("telemetry", arrow_table)
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS row_count,
                    COUNT(DISTINCT vehicle_registration) AS distinct_vehicle_count,
                    MIN(recorded_at) AS first_recorded_at,
                    MAX(recorded_at) AS last_recorded_at
                FROM telemetry
                """
            ).fetchone()
            day_rows = connection.execute(
                """
                SELECT
                    CAST(recorded_at AS DATE) AS recorded_day,
                    COUNT(*) AS row_count
                FROM telemetry
                WHERE recorded_at IS NOT NULL
                GROUP BY 1
                ORDER BY 1 ASC
                """
            ).fetchall()
            vehicle_rows = connection.execute(
                """
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
            ).fetchall()

        if row is None:
            raise RuntimeError("DuckDB did not return a summary row.")

        return TelemetryAnalyticsSummary(
            stored_filename=query.stored_filename,
            processed_path=Path(f"{self._settings.iceberg_namespace}/{self._settings.iceberg_table_name}"),
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

    def _build_row_filter(self, query: TelemetryAnalyticsQuery) -> BooleanExpression:
        row_filter: BooleanExpression = self._equal_to(
            "stored_filename",
            query.stored_filename,
        )
        if query.vehicle_registration:
            row_filter = And(
                row_filter,
                self._equal_to("vehicle_registration", query.vehicle_registration),
            )
        if query.start_recorded_at:
            row_filter = And(
                row_filter,
                self._greater_than_or_equal(
                    "recorded_at",
                    self._parse_recorded_at(query.start_recorded_at),
                ),
            )
        if query.end_recorded_at:
            row_filter = And(
                row_filter,
                self._less_than_or_equal(
                    "recorded_at",
                    self._parse_recorded_at(query.end_recorded_at),
                ),
            )
        return row_filter

    def _equal_to(self, term: str, value: object) -> BooleanExpression:
        return EqualTo(term, value=value)  # type: ignore[misc, arg-type]

    def _greater_than_or_equal(self, term: str, value: object) -> BooleanExpression:
        return GreaterThanOrEqual(term, value=value)  # type: ignore[misc, arg-type]

    def _less_than_or_equal(self, term: str, value: object) -> BooleanExpression:
        return LessThanOrEqual(term, value=value)  # type: ignore[misc, arg-type]

    def _parse_recorded_at(self, value: str) -> datetime:
        normalized_value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized_value)

    def _to_iso_string(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value).replace(" ", "T", 1)
