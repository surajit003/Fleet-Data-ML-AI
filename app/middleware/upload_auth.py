from fastapi import Request, status
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

from app.core.config import get_settings

UPLOAD_TELEMETRY_PATH = "/api/v1/uploads/telemetry"


async def enforce_upload_api_key(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    if request.method != "POST" or request.url.path != UPLOAD_TELEMETRY_PATH:
        return await call_next(request)

    settings = get_settings()
    if settings.api_key is None:
        return await call_next(request)

    api_key = request.headers.get("x-api-key")
    if api_key != settings.api_key:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or missing API key."},
        )

    return await call_next(request)
