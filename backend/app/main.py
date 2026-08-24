from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.routers.health import router as root_health_router
from app.core.logger import logger
from app.core.rate_limit import SlidingWindowLimiter


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="企业安全运营平台后端 API",
    )
    application.include_router(api_router, prefix="/api/v1")
    application.include_router(root_health_router)
    logger.info("application initialized environment=%s", settings.environment)
    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    application.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])
    request_limiter = SlidingWindowLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)

    @application.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Health checks must remain available to orchestrators and monitoring.
        if request.url.path != "/health":
            client_ip = request.client.host if request.client else "unknown"
            if not request_limiter.allow(client_ip):
                logger.warning("request rate limit exceeded ip=%s path=%s", client_ip, request.url.path)
                return JSONResponse(status_code=429, content={"code": "HTTP_429", "message": "请求过于频繁，请稍后再试", "details": {}})
        return await call_next(request)

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("validation error path=%s errors=%s", request.url.path, exc.errors())
        return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR", "message": "请求参数校验失败", "details": exc.errors()})

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"code": f"HTTP_{exc.status_code}", "message": exc.detail, "details": {}})

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error path=%s", request.url.path)
        return JSONResponse(status_code=500, content={"code": "INTERNAL_ERROR", "message": "服务器内部错误", "details": {}})
    return application


app = create_app()
