from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.health import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="服务健康检查")
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="backend",
        timestamp=datetime.now(timezone.utc),
    )
