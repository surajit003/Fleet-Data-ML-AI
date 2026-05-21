from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints.uploads import ui_router as uploads_ui_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.repositories.sqlite_upload_audit_repository import (
    initialize_upload_metadata_database,
)

SettingsDep = Annotated[Settings, Depends(get_settings)]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    initialize_upload_metadata_database(settings.upload_metadata_db_path)
    logger = get_logger().bind(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
    logger.info("application_startup")
    app.state.settings = settings
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    static_dir = Path(__file__).resolve().parent / "static"

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(uploads_ui_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["meta"])
    def read_root(app_settings: SettingsDep) -> dict[str, str]:
        return {
            "service": app_settings.app_name,
            "version": app_settings.app_version,
            "docs": "/docs",
            "health": f"{app_settings.api_v1_prefix}/health",
        }

    return app


app = create_app()
