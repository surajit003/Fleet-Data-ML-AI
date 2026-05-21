from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.services.health_service import HealthService
from app.core.config import Settings, get_settings
from app.domain.repositories.health_repository import HealthRepository
from app.infrastructure.repositories.static_health_repository import StaticHealthRepository
from app.schemas.health import HealthResponse

router = APIRouter()

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_health_repository(
    settings: SettingsDep,
) -> HealthRepository:
    return StaticHealthRepository(settings=settings)


HealthRepositoryDep = Annotated[HealthRepository, Depends(get_health_repository)]


def get_health_service(
    repository: HealthRepositoryDep,
) -> HealthService:
    return HealthService(repository=repository)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]


@router.get("/health", response_model=HealthResponse)
def read_health(service: HealthServiceDep) -> HealthResponse:
    health_status = service.get_health_status()

    return HealthResponse(
        status=health_status.status,
        service=health_status.service,
        version=health_status.version,
        environment=health_status.environment,
    )
