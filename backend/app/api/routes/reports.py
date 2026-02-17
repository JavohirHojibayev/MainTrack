from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.rbac import require_roles
from app.models.employee import Employee
from app.models.user import User
from app.models.event import Event, EventStatus, EventType
from app.schemas.report import InsideMineItem, MineWorkSummaryItem, ToolDebtItem

router = APIRouter()


@router.get("/inside-mine", response_model=list[InsideMineItem])
def inside_mine(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> list[InsideMineItem]:
    subq = (
        db.query(
            Event.employee_id.label("employee_id"),
            func.max(case((Event.event_type == EventType.MINE_IN, Event.event_ts), else_=None)).label("last_in"),
            func.max(case((Event.event_type == EventType.MINE_OUT, Event.event_ts), else_=None)).label("last_out"),
        )
        .filter(Event.status == EventStatus.ACCEPTED)
        .group_by(Event.employee_id)
        .subquery()
    )

    rows = (
        db.query(Employee, subq.c.last_in, subq.c.last_out)
        .join(subq, subq.c.employee_id == Employee.id)
        .filter(subq.c.last_in.isnot(None))
        .filter((subq.c.last_out.is_(None)) | (subq.c.last_in > subq.c.last_out))
        .all()
    )

    result: list[InsideMineItem] = []
    for emp, last_in, _last_out in rows:
        full_name = f"{emp.last_name} {emp.first_name} {emp.patronymic or ''}".strip()
        result.append(
            InsideMineItem(
                employee_id=emp.id,
                employee_no=emp.employee_no,
                full_name=full_name,
                last_in=last_in,
            )
        )
    return result


@router.get("/tool-debts", response_model=list[ToolDebtItem])
def tool_debts(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> list[ToolDebtItem]:
    subq = (
        db.query(
            Event.employee_id.label("employee_id"),
            func.max(case((Event.event_type == EventType.TOOL_TAKE, Event.event_ts), else_=None)).label("last_take"),
            func.max(case((Event.event_type == EventType.TOOL_RETURN, Event.event_ts), else_=None)).label("last_return"),
        )
        .filter(Event.status == EventStatus.ACCEPTED)
        .group_by(Event.employee_id)
        .subquery()
    )

    rows = (
        db.query(Employee, subq.c.last_take, subq.c.last_return)
        .join(subq, subq.c.employee_id == Employee.id)
        .filter(subq.c.last_take.isnot(None))
        .filter((subq.c.last_return.is_(None)) | (subq.c.last_take > subq.c.last_return))
        .all()
    )

    result: list[ToolDebtItem] = []
    for emp, last_take, _last_return in rows:
        full_name = f"{emp.last_name} {emp.first_name} {emp.patronymic or ''}".strip()
        result.append(
            ToolDebtItem(
                employee_id=emp.id,
                employee_no=emp.employee_no,
                full_name=full_name,
                last_take=last_take,
            )
        )
    return result


@router.get("/daily-mine-summary", response_model=list[MineWorkSummaryItem])
def daily_mine_summary(
    day: date = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> list[MineWorkSummaryItem]:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    events = (
        db.query(Event)
        .filter(
            Event.status == EventStatus.ACCEPTED,
            Event.event_type.in_([EventType.MINE_IN, EventType.MINE_OUT]),
            Event.event_ts >= start,
            Event.event_ts <= end + timedelta(days=1),
        )
        .order_by(Event.employee_id, Event.event_ts)
        .all()
    )

    summary: dict[int, dict] = {}
    current_in: dict[int, datetime] = {}

    for ev in events:
        emp_id = ev.employee_id
        if emp_id not in summary:
            summary[emp_id] = {
                "total_minutes": 0,
                "last_in": None,
                "last_out": None,
                "is_inside": False
            }
        
        entry = summary[emp_id]

        if ev.event_type == EventType.MINE_IN:
            if start <= ev.event_ts < end:
                current_in[emp_id] = ev.event_ts
                entry["last_in"] = ev.event_ts
                entry["is_inside"] = True
        elif ev.event_type == EventType.MINE_OUT:
            entry["last_out"] = ev.event_ts
            entry["is_inside"] = False
            if emp_id in current_in:
                in_ts = current_in.pop(emp_id)
                duration = ev.event_ts - in_ts
                minutes = int(duration.total_seconds() // 60)
                entry["total_minutes"] += max(minutes, 0)

    # For those still inside, calculate duration until now (if today)
    for emp_id, in_ts in current_in.items():
        pass # Do not calculate duration for active sessions

    if not summary:
        return []

    employees = db.query(Employee).filter(Employee.id.in_(list(summary.keys()))).all()
    by_id = {emp.id: emp for emp in employees}

    result: list[MineWorkSummaryItem] = []
    for emp_id, data in summary.items():
        emp = by_id.get(emp_id)
        if not emp:
            continue
        full_name = f"{emp.last_name} {emp.first_name} {emp.patronymic or ''}".strip()
        result.append(
            MineWorkSummaryItem(
                employee_id=emp.id,
                employee_no=emp.employee_no,
                full_name=full_name,
                total_minutes=data["total_minutes"],
                last_in=data["last_in"],
                last_out=data["last_out"],
                is_inside=data["is_inside"],
            )
        )
    return result


@router.get("/blocked-attempts", response_model=list[dict])
def blocked_attempts(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
    limit: int = Query(default=200, ge=1, le=2000),
) -> list[dict]:
    events = (
        db.query(Event)
        .filter(Event.status == EventStatus.REJECTED)
        .order_by(Event.event_ts.desc())
        .limit(limit)
        .all()
    )
    result: list[dict] = []
    for ev in events:
        result.append(
            {
                "id": ev.id,
                "employee_id": ev.employee_id,
                "device_id": ev.device_id,
                "event_type": ev.event_type,
                "event_ts": ev.event_ts,
                "raw_id": ev.raw_id,
                "reject_reason": ev.reject_reason,
            }
        )
    return result


@router.get("/esmo-summary", response_model=int)
def esmo_summary(
    day: date = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> int:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    count = (
        db.query(func.count(func.distinct(Event.employee_id)))
        .filter(
            Event.status == EventStatus.ACCEPTED,
            Event.event_type == EventType.ESMO_OK,
            Event.event_ts >= start,
            Event.event_ts < end,
        )
        .scalar()
    )
    return count or 0
