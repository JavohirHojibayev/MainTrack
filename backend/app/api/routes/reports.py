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
from app.schemas.report import InsideMineItem, MineWorkSummaryItem, ToolDebtItem, ReportSummary

router = APIRouter()


@router.get("/summary", response_model=ReportSummary)
def get_report_summary(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> ReportSummary:
    # Query to count all event types in one go
    counts = (
        db.query(Event.event_type, func.count(Event.id))
        .filter(Event.event_ts >= date_from, Event.event_ts <= date_to)
        .group_by(Event.event_type)
        .all()
    )
    
    mapping = {row[0]: row[1] for row in counts}
    
    # Blocked attempts (status REJECTED)
    blocked_count = (
        db.query(func.count(Event.id))
        .filter(Event.status == EventStatus.REJECTED)
        .filter(Event.event_ts >= date_from, Event.event_ts <= date_to)
        .scalar()
    ) or 0

    return ReportSummary(
        turnstile_in=mapping.get(EventType.TURNSTILE_IN, 0),
        turnstile_out=mapping.get(EventType.TURNSTILE_OUT, 0),
        esmo_ok=mapping.get(EventType.ESMO_OK, 0),
        esmo_fail=mapping.get(EventType.ESMO_FAIL, 0),
        tool_takes=mapping.get(EventType.TOOL_TAKE, 0),
        tool_returns=mapping.get(EventType.TOOL_RETURN, 0),
        mine_in=mapping.get(EventType.MINE_IN, 0),
        mine_out=mapping.get(EventType.MINE_OUT, 0),
        blocked=blocked_count
    )


@router.get("/inside-mine", response_model=list[InsideMineItem])
def inside_mine(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> list[InsideMineItem]:
    subq = (
        db.query(
            Event.employee_id.label("employee_id"),
            func.max(case((Event.event_type == EventType.MINE_IN, Event.event_ts), else_=None)).label("last_in"),
            func.max(case((Event.event_type.in_([EventType.MINE_OUT, EventType.TURNSTILE_OUT]), Event.event_ts), else_=None)).label("last_out"),
        )
        .filter(Event.status == EventStatus.ACCEPTED)
        .group_by(Event.employee_id)
        .subquery()
    )

    # Filter to only show people who entered in the recently (e.g. last 24h)
    # This matches the "Daily Activity" logic which filters out ghost records from days ago
    TZ = timezone(timedelta(hours=5))
    cutoff = datetime.now(TZ) - timedelta(hours=24)
    
    rows = (
        db.query(Employee, subq.c.last_in, subq.c.last_out)
        .join(subq, subq.c.employee_id == Employee.id)
        .filter(subq.c.last_in.isnot(None))
        .filter(subq.c.last_in >= cutoff)
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
    TZ = timezone(timedelta(hours=5))
    start = datetime(day.year, day.month, day.day, tzinfo=TZ)
    end = start + timedelta(days=1)
    
    # Look back 16 hours (for 10-hour shifts) to catch overnight shifts
    query_start = start - timedelta(hours=16)
    
    events = (
        db.query(Event)
        .filter(
            Event.status == EventStatus.ACCEPTED,
            Event.event_type.in_([EventType.MINE_IN, EventType.MINE_OUT, EventType.TURNSTILE_OUT]),
            Event.event_ts >= query_start,
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
                "is_inside": False,
                # Track if they have activity TODAY so we filter correctly
                "has_activity_today": False
            }
        
        entry = summary[emp_id]
        
        # Check if event is within the requested day (start <= ts < end)
        is_today = start <= ev.event_ts < end
        if is_today:
            entry["has_activity_today"] = True

        if ev.event_type == EventType.MINE_IN:
            current_in[emp_id] = ev.event_ts
            entry["last_in"] = ev.event_ts
            entry["is_inside"] = True
        elif ev.event_type in [EventType.MINE_OUT, EventType.TURNSTILE_OUT]:
            # Only record as exit if they were arguably inside or we are just tracking the last exit event
            # If they have multiple outs, we just update last_out
            entry["last_out"] = ev.event_ts
            entry["is_inside"] = False
            if emp_id in current_in:
                # We don't need to accumulate total minutes for previous sessions anymore
                # because the UI shows "Last In" / "Last Out", so Duration should match that interval.
                current_in.pop(emp_id)

    # Calculate session duration based on Last In / Last Out
    now = datetime.now(TZ)
    
    if not summary:
        return []

    employees = db.query(Employee).filter(Employee.id.in_(list(summary.keys()))).all()
    by_id = {emp.id: emp for emp in employees}

    cutoff_inside = start - timedelta(hours=12)

    result: list[MineWorkSummaryItem] = []
    for emp_id, data in summary.items():
        is_active_today = data["has_activity_today"]
        is_inside_from_recent = data["is_inside"] and data["last_in"] and data["last_in"] >= cutoff_inside

        # Only include if they have activity today OR are currently inside from a recent shift (e.g. night shift)
        if not (is_active_today or is_inside_from_recent):
             continue

        emp = by_id.get(emp_id)
        if not emp:
            continue
        
        # If currently inside, previous exit time is irrelevant/confusing for "Daily Activity" row
        final_last_out = data["last_out"] if not data["is_inside"] else None

        # Calculate duration based on the DISPLAYED session (Last In -> Last Out/Now)
        # This fixes the confusion where "Total Daily Duration" > "Interval shown"
        session_minutes = 0
        if data["last_in"]:
            # Ensure timezone awareness
            l_in = data["last_in"]
            if l_in.tzinfo is None: l_in = l_in.replace(tzinfo=TZ)
            
            if data["is_inside"]:
                # Currently inside: Duration = Now - Last In
                if now > l_in:
                    duration = now - l_in
                    session_minutes = int(duration.total_seconds() // 60)
            elif data["last_out"]:
                # Currently outside: Duration = Last Out - Last In
                l_out = data["last_out"]
                if l_out.tzinfo is None: l_out = l_out.replace(tzinfo=TZ)
                
                if l_out > l_in:
                    duration = l_out - l_in
                    session_minutes = int(duration.total_seconds() // 60)

        full_name = f"{emp.last_name} {emp.first_name} {emp.patronymic or ''}".strip()
        result.append(
            MineWorkSummaryItem(
                employee_id=emp.id,
                employee_no=emp.employee_no,
                full_name=full_name,
                total_minutes=max(session_minutes, 0),
                last_in=data["last_in"],
                last_out=final_last_out,
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
    TZ = timezone(timedelta(hours=5))
    start = datetime(day.year, day.month, day.day, tzinfo=TZ)
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
