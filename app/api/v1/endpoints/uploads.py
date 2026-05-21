from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.application.services.telemetry_upload_service import TelemetryUploadService
from app.core.config import Settings, get_settings
from app.domain.entities.telemetry_upload_payload import TelemetryUploadPayload
from app.domain.exceptions import InvalidTelemetryUploadError
from app.domain.repositories.upload_storage_repository import UploadStorageRepository
from app.domain.telemetry_schema import TRACKZEE_COLUMNS
from app.infrastructure.repositories.local_upload_storage_repository import (
    LocalUploadStorageRepository,
)
from app.schemas.uploads import TelemetryUploadResponse

router = APIRouter(prefix="/uploads")

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_upload_storage_repository(settings: SettingsDep) -> UploadStorageRepository:
    return LocalUploadStorageRepository(storage_dir=settings.upload_storage_dir)


UploadStorageRepositoryDep = Annotated[
    UploadStorageRepository,
    Depends(get_upload_storage_repository),
]


def get_telemetry_upload_service(
    settings: SettingsDep,
    repository: UploadStorageRepositoryDep,
) -> TelemetryUploadService:
    return TelemetryUploadService(
        storage_repository=repository,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )


TelemetryUploadServiceDep = Annotated[
    TelemetryUploadService,
    Depends(get_telemetry_upload_service),
]


@router.post(
    "/telemetry",
    response_model=TelemetryUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_telemetry_csv(
    file: Annotated[UploadFile, File(...)],
    service: TelemetryUploadServiceDep,
) -> TelemetryUploadResponse:
    filename = file.filename or ""
    content = await file.read()

    try:
        result = service.upload_csv(
            TelemetryUploadPayload(
                filename=filename,
                content_type=file.content_type or "text/csv",
                content=content,
            )
        )
    except InvalidTelemetryUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await file.close()

    return TelemetryUploadResponse(
        filename=result.upload.original_filename,
        stored_filename=result.upload.stored_filename,
        content_type=result.upload.content_type,
        size_bytes=result.upload.size_bytes,
        row_count=result.upload.row_count,
        accepted_columns=list(TRACKZEE_COLUMNS),
        mapped_fields=result.mapped_fields,
    )
