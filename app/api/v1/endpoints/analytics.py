from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyiceberg.exceptions import NoSuchTableError

from app.application.services.telemetry_analytics_service import (
    TelemetryAnalyticsService,
)
from app.core.config import Settings, get_settings
from app.domain.entities.telemetry_analytics_query import TelemetryAnalyticsQuery
from app.domain.repositories.telemetry_analytics_repository import (
    TelemetryAnalyticsRepository,
)
from app.infrastructure.repositories.bigquery_telemetry_analytics_repository import (
    BigQueryTelemetryAnalyticsRepository,
)
from app.infrastructure.repositories.duckdb_telemetry_analytics_repository import (
    DuckDBTelemetryAnalyticsRepository,
)
from app.schemas.analytics import (
    TelemetryAnalyticsBreakdownRowResponse,
    TelemetryAnalyticsSummaryResponse,
)

router = APIRouter(prefix="/analytics")

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_telemetry_analytics_service(
    settings: SettingsDep,
) -> TelemetryAnalyticsService:
    repository: TelemetryAnalyticsRepository
    if settings.analytics_backend == "bigquery":
        repository = BigQueryTelemetryAnalyticsRepository(settings=settings)
    else:
        repository = DuckDBTelemetryAnalyticsRepository(settings=settings)
    return TelemetryAnalyticsService(repository=repository)


TelemetryAnalyticsServiceDep = Annotated[
    TelemetryAnalyticsService,
    Depends(get_telemetry_analytics_service),
]


@router.get(
    "/telemetry/{stored_filename}/summary",
    response_model=TelemetryAnalyticsSummaryResponse,
)
def read_telemetry_summary(
    stored_filename: str,
    service: TelemetryAnalyticsServiceDep,
    vehicle_registration: Annotated[str | None, Query()] = None,
    start_recorded_at: Annotated[str | None, Query()] = None,
    end_recorded_at: Annotated[str | None, Query()] = None,
) -> TelemetryAnalyticsSummaryResponse:
    try:
        summary = service.summarize_curated_upload(
            TelemetryAnalyticsQuery(
                stored_filename=stored_filename,
                vehicle_registration=vehicle_registration,
                start_recorded_at=start_recorded_at,
                end_recorded_at=end_recorded_at,
            )
        )
    except NoSuchTableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curated upload not found.",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curated upload not found.",
        ) from exc

    return TelemetryAnalyticsSummaryResponse(
        stored_filename=summary.stored_filename,
        processed_path=str(summary.processed_path),
        row_count=summary.row_count,
        distinct_vehicle_count=summary.distinct_vehicle_count,
        first_recorded_at=summary.first_recorded_at,
        last_recorded_at=summary.last_recorded_at,
        records_by_day=[
            TelemetryAnalyticsBreakdownRowResponse(label=row.label, count=row.count)
            for row in summary.records_by_day
        ],
        records_by_vehicle=[
            TelemetryAnalyticsBreakdownRowResponse(label=row.label, count=row.count)
            for row in summary.records_by_vehicle
        ],
        vehicle_registration=vehicle_registration,
        start_recorded_at=start_recorded_at,
        end_recorded_at=end_recorded_at,
    )
