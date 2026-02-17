from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class InsideMineItem(BaseModel):
    employee_id: int
    employee_no: str
    full_name: str
    last_in: datetime | None


class ToolDebtItem(BaseModel):
    employee_id: int
    employee_no: str
    full_name: str
    last_take: datetime | None


class MineWorkSummaryItem(BaseModel):
    employee_id: int
    employee_no: str
    full_name: str
    total_minutes: int
    last_in: datetime | None = None
    last_out: datetime | None = None
    is_inside: bool = False
