from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.assets import router as assets_router
from app.api.routes.scans import router as scans_router
from app.api.routes.vulnerabilities import router as vulnerabilities_router
from app.api.routes.risk import router as risk_router
from app.api.routes.audit import router as audit_router
from app.api.routes.schedules import router as schedules_router
from app.api.routes.cve import router as cve_router
from app.api.routes.reports import router as reports_router


api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(assets_router, tags=["assets"])
api_router.include_router(scans_router, tags=["scans"])
api_router.include_router(vulnerabilities_router, tags=["vulnerabilities"])
api_router.include_router(risk_router, tags=["risk"])
api_router.include_router(audit_router, tags=["audit"])
api_router.include_router(schedules_router, tags=["scan-schedules"])
api_router.include_router(cve_router, tags=["cve"])
api_router.include_router(reports_router, tags=["reports"])
