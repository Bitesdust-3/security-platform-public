from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress


class AssetServiceCreate(BaseModel):
    port: int = Field(ge=1, le=65535)
    protocol: str = Field(min_length=1, max_length=16)
    service_name: str | None = Field(default=None, max_length=128)
    service_version: str | None = Field(default=None, max_length=128)


class AssetServiceResponse(AssetServiceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    discovered_at: datetime | None


class AssetCreate(BaseModel):
    asset_name: str = Field(min_length=1, max_length=128)
    asset_type: str = Field(min_length=1, max_length=32)
    ip_address: IPvAnyAddress | None = None
    hostname: str | None = Field(default=None, max_length=255)
    os_info: str | None = Field(default=None, max_length=255)
    environment: str | None = Field(default=None, max_length=32)
    importance: int = Field(default=3, ge=1, le=5)
    owner: str | None = Field(default=None, max_length=128)
    description: str | None = None


class AssetUpdate(BaseModel):
    asset_name: str | None = Field(default=None, min_length=1, max_length=128)
    asset_type: str | None = Field(default=None, min_length=1, max_length=32)
    ip_address: IPvAnyAddress | None = None
    hostname: str | None = Field(default=None, max_length=255)
    os_info: str | None = Field(default=None, max_length=255)
    environment: str | None = Field(default=None, max_length=32)
    importance: int | None = Field(default=None, ge=1, le=5)
    owner: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, pattern="^(active|inactive|unknown)$")
    description: str | None = None


class AssetResponse(AssetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ip_address: IPv4Address | IPv6Address | None
    status: str
    created_at: datetime
    updated_at: datetime
    services: list[AssetServiceResponse] = []


class AssetListResponse(BaseModel):
    data: list[AssetResponse]
    page: int
    page_size: int
    total: int
