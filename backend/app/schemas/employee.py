from __future__ import annotations

from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    employee_no: str = Field(..., min_length=1, max_length=32)
    first_name: str
    last_name: str
    patronymic: str | None = None
    department: str | None = None
    position: str | None = None


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    department: str | None = None
    position: str | None = None
    is_active: bool | None = None


class EmployeeOut(BaseModel):
    id: int
    employee_no: str
    first_name: str
    last_name: str
    patronymic: str | None = None
    department: str | None = None
    position: str | None = None
    is_active: bool

    class Config:
        from_attributes = True
