from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, Response

from app.application.services.telemetry_transform_service import TelemetryTransformService
from app.application.services.telemetry_upload_service import TelemetryUploadService
from app.core.config import Settings, get_settings
from app.domain.entities.duplicate_row_diagnostic import DuplicateRowDiagnostic
from app.domain.entities.telemetry_upload_payload import TelemetryUploadPayload
from app.domain.entities.upload_audit_detail import UploadAuditDetail
from app.domain.entities.upload_audit_record import UploadAuditRecord
from app.domain.entities.upload_sanity_summary import UploadSanitySummary
from app.domain.exceptions import InvalidTelemetryUploadError
from app.domain.repositories.upload_audit_repository import UploadAuditRepository
from app.domain.repositories.upload_storage_repository import UploadStorageRepository
from app.domain.telemetry_schema import (
    REQUIRED_TELEMETRY_COLUMNS,
    SAMPLE_TELEMETRY_ROW,
    TELEMETRY_FIELD_GUIDE,
)
from app.domain.upload_status import (
    STATUS_READY_FOR_TRANSFORM,
    can_prepare_for_transform,
    can_run_transform,
    derive_validation_status,
)
from app.infrastructure.repositories.local_upload_storage_repository import (
    LocalUploadStorageRepository,
)
from app.infrastructure.repositories.sqlite_upload_audit_repository import (
    SqliteUploadAuditRepository,
)
from app.schemas.uploads import (
    DuplicateRowDiagnosticResponse,
    TelemetryColumnIssue,
    TelemetryPreviewRow,
    TelemetrySanitySummary,
    TelemetryUploadResponse,
    UploadAuditRecordResponse,
    UploadDetailResponse,
    UploadHistoryResponse,
)

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


def get_upload_audit_repository(settings: SettingsDep) -> UploadAuditRepository:
    return SqliteUploadAuditRepository(database_path=settings.upload_metadata_db_path)


UploadAuditRepositoryDep = Annotated[
    UploadAuditRepository,
    Depends(get_upload_audit_repository),
]


def get_telemetry_transform_service(settings: SettingsDep) -> TelemetryTransformService:
    return TelemetryTransformService(
        raw_storage_dir=settings.upload_storage_dir,
        processed_storage_dir=settings.processed_storage_dir,
        duplicate_strategy=settings.duplicate_strategy,
    )


TelemetryTransformServiceDep = Annotated[
    TelemetryTransformService,
    Depends(get_telemetry_transform_service),
]


def get_telemetry_upload_service(
    settings: SettingsDep,
    audit_repository: UploadAuditRepositoryDep,
    repository: UploadStorageRepositoryDep,
) -> TelemetryUploadService:
    return TelemetryUploadService(
        audit_repository=audit_repository,
        storage_repository=repository,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )


TelemetryUploadServiceDep = Annotated[
    TelemetryUploadService,
    Depends(get_telemetry_upload_service),
]


def require_upload_api_key(
    settings: SettingsDep,
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if settings.api_key is None:
        return
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


UploadApiKeyDep = Annotated[None, Depends(require_upload_api_key)]


def _render_upload_page(app_name: str, api_prefix: str) -> str:
    grouped_fields: dict[str, list[str]] = {}
    for field in TELEMETRY_FIELD_GUIDE:
        badge_class = (
            "badge optional"
            if field.value_requirement == "Optional value"
            else "badge required"
        )
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


def _to_upload_audit_record_response(
    upload: UploadAuditRecord,
) -> UploadAuditRecordResponse:
    return UploadAuditRecordResponse(
        status=upload.status,
        stored_filename=upload.stored_filename,
        original_filename=upload.original_filename,
        content_type=upload.content_type,
        size_bytes=upload.size_bytes,
        row_count=upload.row_count,
        unique_vehicle_count=upload.unique_vehicle_count,
        warning_count=upload.warning_count,
        warnings=list(upload.warnings),
        first_recorded_at=upload.first_recorded_at,
        last_recorded_at=upload.last_recorded_at,
        processed_path=upload.processed_path,
        transformed_row_count=upload.transformed_row_count,
        duplicate_row_count=upload.duplicate_row_count,
        transformed_at=upload.transformed_at,
        created_at=upload.created_at,
    )


def _to_sanity_summary_response(
    sanity_summary: UploadSanitySummary,
) -> TelemetrySanitySummary:
    return TelemetrySanitySummary(
        preview_columns=list(sanity_summary.preview_columns),
        preview_rows=[
            TelemetryPreviewRow(row_number=row.row_number, values=row.values)
            for row in sanity_summary.preview_rows
        ],
        warnings=list(sanity_summary.warnings),
        required_value_issues=[
            TelemetryColumnIssue(
                column=issue.column,
                issue=issue.issue,
                affected_rows=issue.affected_rows,
            )
            for issue in sanity_summary.required_value_issues
        ],
        unique_vehicle_count=sanity_summary.unique_vehicle_count,
        first_recorded_at=sanity_summary.first_recorded_at,
        last_recorded_at=sanity_summary.last_recorded_at,
    )


def _to_duplicate_diagnostics_response(
    duplicate_diagnostics: tuple[DuplicateRowDiagnostic, ...],
) -> list[DuplicateRowDiagnosticResponse]:
    return [
        DuplicateRowDiagnosticResponse(
            row_number=item.row_number,
            duplicate_of_row_number=item.duplicate_of_row_number,
            duplicate_key=item.duplicate_key,
            device_imei=item.device_imei,
            vehicle_registration=item.vehicle_registration,
            recorded_at=item.recorded_at,
            reason=item.reason,
        )
        for item in duplicate_diagnostics
    ]


def _to_upload_detail_response(detail: UploadAuditDetail) -> UploadDetailResponse:
    return UploadDetailResponse(
        upload=_to_upload_audit_record_response(detail.upload),
        sanity_summary=_to_sanity_summary_response(detail.sanity_summary),
        duplicate_diagnostics=_to_duplicate_diagnostics_response(
            detail.duplicate_diagnostics
        ),
    )


@ui_router.get("/upload", response_class=HTMLResponse, tags=["ui"])
def read_upload_page(app_settings: SettingsDep) -> str:
    return _render_upload_page(
        app_name=app_settings.app_name,
        api_prefix=app_settings.api_v1_prefix,
    )


@ui_router.get("/upload/sample", tags=["ui"])
def download_sample_csv() -> Response:
    csv_content = (
        ",".join(REQUIRED_TELEMETRY_COLUMNS)
        + "\n"
        + ",".join(SAMPLE_TELEMETRY_ROW)
        + "\n"
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="telemetry-sample.csv"'},
    )


@router.get("/history", response_model=UploadHistoryResponse)
def read_upload_history(
    repository: UploadAuditRepositoryDep,
) -> UploadHistoryResponse:
    uploads = repository.list_recent_uploads()
    return UploadHistoryResponse(
        uploads=[_to_upload_audit_record_response(upload) for upload in uploads]
    )


@router.get("/history/{stored_filename}", response_model=UploadDetailResponse)
def read_upload_detail(
    stored_filename: str,
    repository: UploadAuditRepositoryDep,
) -> UploadDetailResponse:
    detail = repository.get_upload_detail(stored_filename)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")

    return _to_upload_detail_response(detail)


@router.post("/history/{stored_filename}/prepare-transform", response_model=UploadDetailResponse)
def prepare_upload_for_transform(
    stored_filename: str,
    repository: UploadAuditRepositoryDep,
) -> UploadDetailResponse:
    detail = repository.get_upload_detail(stored_filename)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")
    if not can_prepare_for_transform(detail.upload.status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload is not in a state that can be prepared for transform.",
        )

    updated_detail = repository.update_upload_status(stored_filename, STATUS_READY_FOR_TRANSFORM)
    if updated_detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")

    return _to_upload_detail_response(updated_detail)


@router.post("/history/{stored_filename}/run-transform", response_model=UploadDetailResponse)
def run_transform_for_upload(
    stored_filename: str,
    repository: UploadAuditRepositoryDep,
    transform_service: TelemetryTransformServiceDep,
) -> UploadDetailResponse:
    detail = repository.get_upload_detail(stored_filename)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")
    if not can_run_transform(detail.upload.status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload is not ready to run transform.",
        )

    try:
        result = transform_service.transform_upload(stored_filename)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raw upload file could not be found for transform.",
        ) from exc

    updated_detail = repository.mark_upload_transformed(
        stored_filename=stored_filename,
        processed_path=result.processed_path,
        transformed_row_count=result.row_count,
        duplicate_row_count=result.duplicate_row_count,
        duplicate_diagnostics=result.duplicate_diagnostics,
    )
    if updated_detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")

    return _to_upload_detail_response(updated_detail)


@router.get("/history/{stored_filename}/processed-artifact")
def download_processed_artifact(
    stored_filename: str,
    repository: UploadAuditRepositoryDep,
) -> FileResponse:
    detail = repository.get_upload_detail(stored_filename)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")

    processed_path = detail.upload.processed_path
    if not processed_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload does not have a processed artifact yet.",
        )

    path = Path(processed_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processed artifact could not be found.",
        )

    return FileResponse(path, media_type="text/csv", filename=path.name)


@router.post(
    "/telemetry",
    response_model=TelemetryUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_telemetry_csv(
    file: Annotated[UploadFile, File(...)],
    _: UploadApiKeyDep,
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
        status=derive_validation_status(result.sanity_summary),
        filename=result.upload.original_filename,
        stored_filename=result.upload.stored_filename,
        content_type=result.upload.content_type,
        size_bytes=result.upload.size_bytes,
        row_count=result.upload.row_count,
        sanity_summary=_to_sanity_summary_response(result.sanity_summary),
    )
