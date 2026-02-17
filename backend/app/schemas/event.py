from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, model_validator

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
    employee_no: str | None = None
    first_name: str | None = None
    last_name: str | None = None

    @property
    def full_name(self) -> str | None:
        if self.first_name and self.last_name:
            return f"{self.last_name} {self.first_name}"
        return None

    @model_validator(mode='before')
    @classmethod
    def flatten_employee(cls, data: Any) -> Any:
        # If data is an ORM object and has 'employee' loaded
        if hasattr(data, "employee") and data.employee:
            # Create a dict from the object to ensure Pydantic can read the new fields
            # Getting basic fields
            obj_dict = {
                "id": data.id,
                "device_id": data.device_id,
                "employee_id": data.employee_id,
                "event_type": data.event_type,
                "event_ts": data.event_ts,
                "received_ts": data.received_ts,
                "raw_id": data.raw_id,
                "status": data.status,
                "reject_reason": data.reject_reason,
            }
            # Add flattened fields
            obj_dict["employee_no"] = data.employee.employee_no
            obj_dict["first_name"] = data.employee.first_name
            obj_dict["last_name"] = data.employee.last_name
            return obj_dict
        return data
