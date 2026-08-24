from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"], summary="基础健康检查")
def health() -> dict[str, str]:
    return {"status": "ok"}
