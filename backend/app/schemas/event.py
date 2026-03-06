from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, model_validator

from app.models.event import EventStatus, EventType

TURNSTILE_NAME_BY_HOST = {
    "192.168.1.181": "shaxta kirish",
    "192.168.1.180": "shaxta chiqish",
}


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
    patronymic: str | None = None
    device_name: str | None = None
    device_host: str | None = None

    @property
    def full_name(self) -> str | None:
        parts = []
        if self.last_name: parts.append(self.last_name)
        if self.first_name: parts.append(self.first_name)
        if self.patronymic: parts.append(self.patronymic)
        
        return " ".join(parts) if parts else None

    @model_validator(mode='before')
    @classmethod
    def flatten_data(cls, data: Any) -> Any:
        try:
            # If data is an ORM object
            if hasattr(data, "id"):
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

                source_payload = getattr(data, "source_payload", None) or {}
                payload_employee_no = str(source_payload.get("employeeNoString") or source_payload.get("cardNo") or "").strip()
                payload_name = str(source_payload.get("name") or "").strip()
                event_type_value = (
                    data.event_type.value if hasattr(data.event_type, "value") else str(data.event_type)
                )
                is_turnstile_event = event_type_value in {
                    "TURNSTILE_IN",
                    "TURNSTILE_OUT",
                    "MINE_IN",
                    "MINE_OUT",
                }
                
                # Flatten Employee
                if hasattr(data, "employee") and data.employee:
                    obj_dict["employee_no"] = data.employee.employee_no
                    obj_dict["first_name"] = data.employee.first_name
                    obj_dict["last_name"] = data.employee.last_name
                    obj_dict["patronymic"] = data.employee.patronymic

                # For turnstile-like events, show raw device identity to avoid cross-domain ID confusion.
                if is_turnstile_event and payload_employee_no:
                    obj_dict["employee_no"] = payload_employee_no
                if is_turnstile_event and payload_name:
                    obj_dict["last_name"] = payload_name
                    obj_dict["first_name"] = None
                    obj_dict["patronymic"] = None
                
                # Flatten Device
                if hasattr(data, "device") and data.device:
                    device_host = data.device.host
                    forced_name = TURNSTILE_NAME_BY_HOST.get(str(device_host or "").strip())
                    obj_dict["device_name"] = forced_name or data.device.name
                    obj_dict["device_host"] = device_host
                    
                return obj_dict
            return data
        except Exception:
            return data


class EventPageOut(BaseModel):
    items: list[EventOut]
    total: int
