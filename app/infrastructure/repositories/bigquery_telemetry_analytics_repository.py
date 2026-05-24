from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from app.core.config import Settings
from app.domain.entities.telemetry_analytics_breakdown_row import (
    TelemetryAnalyticsBreakdownRow,
)
from app.domain.entities.telemetry_analytics_query import TelemetryAnalyticsQuery
from app.domain.entities.telemetry_analytics_summary import TelemetryAnalyticsSummary
from app.domain.repositories.telemetry_analytics_repository import (
    TelemetryAnalyticsRepository,
)


class BigQueryTelemetryAnalyticsRepository(TelemetryAnalyticsRepository):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def summarize_curated_upload(
        self,
        query: TelemetryAnalyticsQuery,
    ) -> TelemetryAnalyticsSummary:
        table_id = self._table_id()
        client = bigquery.Client(project=self._project_id())
        try:
            client.get_table(table_id)
        except NotFound as exc:
            raise FileNotFoundError(query.stored_filename) from exc

        sql, params = self._build_summary_query(table_id, query)
        query_config = bigquery.QueryJobConfig(query_parameters=params)

        row = next(client.query(sql, job_config=query_config).result())
        day_rows = list(
            client.query(
                self._build_records_by_day_query(table_id, query),
                job_config=query_config,
            ).result()
        )
        vehicle_rows = list(
            client.query(
                self._build_records_by_vehicle_query(table_id, query),
                job_config=query_config,
            ).result()
        )

        return TelemetryAnalyticsSummary(
            stored_filename=query.stored_filename,
            processed_path=Path(f"{self._settings.iceberg_namespace}/{self._settings.iceberg_table_name}"),
            row_count=int(row["row_count"]),
            distinct_vehicle_count=int(row["distinct_vehicle_count"]),
            first_recorded_at=self._to_iso_string(row["first_recorded_at"]),
            last_recorded_at=self._to_iso_string(row["last_recorded_at"]),
            records_by_day=tuple(
                TelemetryAnalyticsBreakdownRow(
                    label=str(item["recorded_day"]),
                    count=int(item["row_count"]),
                )
                for item in day_rows
            ),
            records_by_vehicle=tuple(
                TelemetryAnalyticsBreakdownRow(
                    label=str(item["vehicle_registration"]),
                    count=int(item["row_count"]),
                )
                for item in vehicle_rows
            ),
        )

    def _table_id(self) -> str:
        return f"{self._project_id()}.{self._dataset_id()}.{self._settings.iceberg_table_name}"

    def _project_id(self) -> str:
        project_id = self._settings.iceberg_project_id or self._settings.gcp_project_id
        if project_id is None:
            raise ValueError("BigQuery analytics requires a project id.")
        return project_id

    def _dataset_id(self) -> str:
        if self._settings.bigquery_dataset_id is None:
            raise ValueError("BigQuery analytics requires a dataset id.")
        return self._settings.bigquery_dataset_id

    def _build_summary_query(
        self,
        table_id: str,
        query: TelemetryAnalyticsQuery,
    ) -> tuple[str, list[object]]:
        clause, params = self._build_where_clause(query)
        sql = f"""
            WITH telemetry AS (
                SELECT * FROM `{table_id}` WHERE {clause}
            )
            SELECT
                COUNT(*) AS row_count,
                COUNT(DISTINCT vehicle_registration) AS distinct_vehicle_count,
                MIN(TIMESTAMP(recorded_at)) AS first_recorded_at,
                MAX(TIMESTAMP(recorded_at)) AS last_recorded_at
            FROM telemetry
        """
        return sql, params

    def _build_records_by_day_query(
        self,
        table_id: str,
        query: TelemetryAnalyticsQuery,
    ) -> str:
        clause, _ = self._build_where_clause(query)
        return f"""
            WITH telemetry AS (
                SELECT * FROM `{table_id}` WHERE {clause}
            )
            SELECT
                DATE(TIMESTAMP(recorded_at)) AS recorded_day,
                COUNT(*) AS row_count
            FROM telemetry
            WHERE TIMESTAMP(recorded_at) IS NOT NULL
            GROUP BY 1
            ORDER BY 1 ASC
        """

    def _build_records_by_vehicle_query(
        self,
        table_id: str,
        query: TelemetryAnalyticsQuery,
    ) -> str:
        clause, _ = self._build_where_clause(query)
        return f"""
            WITH telemetry AS (
                SELECT * FROM `{table_id}` WHERE {clause}
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

    def _build_where_clause(self, query: TelemetryAnalyticsQuery) -> tuple[str, list[object]]:
        clauses = ["stored_filename = @stored_filename"]
        params: list[object] = [
            bigquery.ScalarQueryParameter(
                "stored_filename",
                "STRING",
                query.stored_filename,
            )
        ]
        if query.vehicle_registration:
            clauses.append("vehicle_registration = @vehicle_registration")
            params.append(
                bigquery.ScalarQueryParameter(
                    "vehicle_registration",
                    "STRING",
                    query.vehicle_registration,
                )
            )
        if query.start_recorded_at:
            clauses.append("TIMESTAMP(recorded_at) >= TIMESTAMP(@start_recorded_at)")
            params.append(
                bigquery.ScalarQueryParameter(
                    "start_recorded_at",
                    "STRING",
                    query.start_recorded_at,
                )
            )
        if query.end_recorded_at:
            clauses.append("TIMESTAMP(recorded_at) <= TIMESTAMP(@end_recorded_at)")
            params.append(
                bigquery.ScalarQueryParameter(
                    "end_recorded_at",
                    "STRING",
                    query.end_recorded_at,
                )
            )
        return " AND ".join(clauses), params

    def _to_iso_string(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value).replace(" ", "T", 1)
