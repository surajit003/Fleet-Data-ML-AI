from fastapi import APIRouter

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.uploads import router as uploads_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(analytics_router, tags=["analytics"])
api_router.include_router(uploads_router, tags=["uploads"])
