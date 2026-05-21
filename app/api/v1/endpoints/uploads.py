from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, Response

from app.application.services.telemetry_upload_service import TelemetryUploadService
from app.core.config import Settings, get_settings
from app.domain.entities.telemetry_upload_payload import TelemetryUploadPayload
from app.domain.exceptions import InvalidTelemetryUploadError
from app.domain.repositories.upload_storage_repository import UploadStorageRepository
from app.domain.telemetry_schema import (
    REQUIRED_TELEMETRY_COLUMNS,
    SAMPLE_TELEMETRY_ROW,
    TELEMETRY_FIELD_GUIDE,
)
from app.infrastructure.repositories.local_upload_storage_repository import (
    LocalUploadStorageRepository,
)
from app.schemas.uploads import TelemetryUploadResponse

router = APIRouter(prefix="/uploads")
ui_router = APIRouter()
UPLOAD_TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "upload.html"
UPLOAD_TEMPLATE = UPLOAD_TEMPLATE_PATH.read_text(encoding="utf-8")

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


def _render_upload_page(app_name: str, api_prefix: str) -> str:
    grouped_fields: dict[str, list[str]] = {}
    for field in TELEMETRY_FIELD_GUIDE:
        badge_class = "badge optional" if field.value_requirement == "Optional value" else "badge required"
        grouped_fields.setdefault(field.group, []).append(
            f"""
            <li>
              <div class="field-topline">
                <code>{field.column}</code>
                <span class="{badge_class}">{field.value_requirement}</span>
              </div>
              <p>{field.description}</p>
              <small>Maps to <code>{field.domain_field}</code></small>
            </li>
            """
        )

    group_sections = []
    for group_name, items in grouped_fields.items():
        group_sections.append(
            f"""
            <section class="group-card">
              <h3>{group_name}</h3>
              <ul class="field-guide">{"".join(items)}</ul>
            </section>
            """
        )

    return (
        UPLOAD_TEMPLATE.replace("__APP_NAME__", app_name)
        .replace("__API_PREFIX__", api_prefix)
        .replace("__COLUMN_COUNT__", str(len(REQUIRED_TELEMETRY_COLUMNS)))
        .replace("__FIELD_GUIDE_HTML__", "".join(group_sections))
    )


@ui_router.get("/upload", response_class=HTMLResponse, tags=["ui"])
def read_upload_page(app_settings: SettingsDep) -> str:
    return _render_upload_page(
        app_name=app_settings.app_name,
        api_prefix=app_settings.api_v1_prefix,
    )


@ui_router.get("/upload/sample", tags=["ui"])
def download_sample_csv() -> Response:
    csv_content = ",".join(REQUIRED_TELEMETRY_COLUMNS) + "\n" + ",".join(SAMPLE_TELEMETRY_ROW) + "\n"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="telemetry-sample.csv"'},
    )


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
        accepted_columns=list(REQUIRED_TELEMETRY_COLUMNS),
        mapped_fields=result.mapped_fields,
    )
