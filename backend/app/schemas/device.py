from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

from app.models.device import DeviceType


class DeviceCreate(BaseModel):
    name: str
    device_code: str = Field(..., min_length=1, max_length=64)
    host: str | None = None
    device_type: DeviceType
    location: str | None = None
    api_key: str | None = None


class DeviceUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    device_type: DeviceType | None = None
    location: str | None = None
    is_active: bool | None = None


class DeviceOut(BaseModel):
    id: int
    name: str
    device_code: str
    host: str | None = None
    device_type: DeviceType
    location: str | None = None
    api_key: str
    is_active: bool
    last_seen: datetime | None = None

    class Config:
        from_attributes = True


class DeviceDataStatusOut(BaseModel):
    device_id: int
    last_data_at: datetime | None = None


class DevicePowerToggle(BaseModel):
    password: str
    is_active: bool
