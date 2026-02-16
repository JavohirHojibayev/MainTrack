from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

from app.models.event import EventStatus, EventType


class EventIn(BaseModel):
    device_code: str
    raw_id: str
    event_type: EventType
    event_ts: datetime
    employee_no: str | None = None
    external_system: str | None = None
    external_id: str | None = None
    payload: dict | None = None


class EventIngestRequest(BaseModel):
    events: list[EventIn] = Field(default_factory=list)


class EventResult(BaseModel):
    raw_id: str
    status: str
    event_id: int | None = None
    reject_reason: str | None = None


class EventOut(BaseModel):
    id: int
    device_id: int
    employee_id: int
    event_type: EventType
    event_ts: datetime
    received_ts: datetime
    raw_id: str
    status: EventStatus
    reject_reason: str | None = None

    class Config:
        from_attributes = True
