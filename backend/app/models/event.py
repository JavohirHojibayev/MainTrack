from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class EventType(str, Enum):
    TURNSTILE_IN = "TURNSTILE_IN"
    TURNSTILE_OUT = "TURNSTILE_OUT"
    ESMO_OK = "ESMO_OK"
    ESMO_FAIL = "ESMO_FAIL"
    TOOL_TAKE = "TOOL_TAKE"
    TOOL_RETURN = "TOOL_RETURN"
    MINE_IN = "MINE_IN"
    MINE_OUT = "MINE_OUT"


class EventStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("minetrack.devices.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("minetrack.employees.id"), nullable=False, index=True)
    event_type = Column(SAEnum(EventType, name="event_type"), nullable=False, index=True)
    event_ts = Column(DateTime(timezone=True), nullable=False, index=True)
    received_ts = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    raw_id = Column(String(128), nullable=False)
    status = Column(SAEnum(EventStatus, name="event_status"), nullable=False, default=EventStatus.ACCEPTED)
    reject_reason = Column(String(255), nullable=True)
    source_payload = Column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("device_id", "raw_id", name="uq_events_device_raw_id"),
    )

    employee = relationship("Employee", back_populates="events")
    device = relationship("Device", back_populates="events")
