from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models import Asset, AssetService
from app.schemas.asset import AssetCreate, AssetListResponse, AssetResponse, AssetServiceCreate, AssetServiceResponse, AssetUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/assets")


def _record_audit(db: DbSession, user_id: int, action: str, resource_id: int, detail: str) -> None:
    record_audit(db, user_id=user_id, action=action, resource="asset", resource_id=resource_id, description=detail)


@router.get("", response_model=AssetListResponse, summary="资产列表")
def list_assets(db: DbSession, _: CurrentUser, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), keyword: str | None = Query(None, max_length=128), ip_address: str | None = Query(None, max_length=45), hostname: str | None = Query(None, max_length=255), asset_type: str | None = Query(None, max_length=32), asset_status: str | None = Query(None, alias="status", pattern="^(active|inactive|unknown)$"), importance: int | None = Query(None, ge=1, le=5)) -> AssetListResponse:
    filters = []
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(or_(Asset.asset_name.like(pattern), Asset.hostname.like(pattern), Asset.ip_address.like(pattern)))
    if ip_address:
        filters.append(Asset.ip_address.like(f"%{ip_address}%"))
    if hostname:
        filters.append(Asset.hostname.like(f"%{hostname}%"))
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if asset_status:
        filters.append(Asset.status == asset_status)
    if importance is not None:
        filters.append(Asset.importance == importance)
    total = db.scalar(select(func.count()).select_from(Asset).where(*filters)) or 0
    items = db.scalars(select(Asset).where(*filters).options(selectinload(Asset.services)).order_by(Asset.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return AssetListResponse(data=items, page=page, page_size=page_size, total=total)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED, summary="创建资产")
def create_asset(payload: AssetCreate, user: AdminUser, db: DbSession) -> Asset:
    asset = Asset(**payload.model_dump(mode="json"), status="active")
    db.add(asset)
    db.flush()
    _record_audit(db, user.id, "create", asset.id, "创建资产")
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=AssetResponse, summary="资产详情")
def get_asset(asset_id: int, _: CurrentUser, db: DbSession) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.id == asset_id).options(selectinload(Asset.services)))
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    return asset


@router.patch("/{asset_id}", response_model=AssetResponse, summary="更新资产")
def update_asset(asset_id: int, payload: AssetUpdate, user: AdminUser, db: DbSession) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    for key, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(asset, key, value)
    _record_audit(db, user.id, "update", asset.id, "更新资产")
    db.commit()
    db.refresh(asset)
    return asset


@router.put("/{asset_id}", response_model=AssetResponse, summary="替换资产")
def replace_asset(asset_id: int, payload: AssetCreate, user: AdminUser, db: DbSession) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    for key, value in payload.model_dump(mode="json").items():
        setattr(asset, key, value)
    _record_audit(db, user.id, "replace", asset.id, "替换资产")
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, summary="停用资产")
def deactivate_asset(asset_id: int, user: AdminUser, db: DbSession) -> None:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    asset.status = "inactive"
    _record_audit(db, user.id, "deactivate", asset.id, "停用资产")
    db.commit()


@router.post("/{asset_id}/services", response_model=AssetServiceResponse, status_code=status.HTTP_201_CREATED, summary="添加资产服务")
def add_service(asset_id: int, payload: AssetServiceCreate, user: AdminUser, db: DbSession) -> AssetService:
    if db.get(Asset, asset_id) is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    service = AssetService(asset_id=asset_id, **payload.model_dump())
    db.add(service)
    db.flush()
    _record_audit(db, user.id, "add_service", asset_id, f"添加服务 {payload.port}/{payload.protocol}")
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{asset_id}/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除资产服务")
def delete_service(asset_id: int, service_id: int, user: AdminUser, db: DbSession) -> None:
    service = db.scalar(select(AssetService).where(AssetService.id == service_id, AssetService.asset_id == asset_id))
    if service is None:
        raise HTTPException(status_code=404, detail="资产服务不存在")
    db.delete(service)
    _record_audit(db, user.id, "delete_service", asset_id, f"删除服务 {service.port}/{service.protocol}")
    db.commit()
