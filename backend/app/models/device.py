from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class DeviceType(str, Enum):
    HIKVISION = "HIKVISION"
    ESMO = "ESMO"
    TOOL_FACE = "TOOL_FACE"
    MINE_FACE = "MINE_FACE"
    OTHER = "OTHER"


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    device_code = Column(String(64), unique=True, nullable=False, index=True)
    host = Column(String(255), nullable=True)
    device_type = Column(SAEnum(DeviceType, name="device_type"), nullable=False)
    location = Column(String(128), nullable=True)
    api_key = Column(String(128), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    events = relationship("Event", back_populates="device")
