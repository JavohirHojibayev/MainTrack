from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.rbac import require_roles
from app.core.esmo_poller import get_allowed_esmo_terminal_names
from app.models.device import Device
from app.models.employee import Employee
from app.models.user import User
from app.models.event import Event, EventStatus, EventType
from app.models.medical_exam import MedicalExam
from app.schemas.report import InsideMineItem, MineWorkSummaryItem, ToolDebtItem, ReportSummary, EsmoSummary24h

router = APIRouter()

TURNSTILE_JOURNAL_HOSTS = {
    "192.168.0.221",
    "192.168.0.224",
    "192.168.0.222",
    "192.168.0.220",
    "192.168.0.219",
    "192.168.0.223",
    "192.168.1.180",
    "192.168.1.181",
}

TURNSTILE_IN_HOSTS = {
    "192.168.0.221",
    "192.168.0.223",
    "192.168.0.219",
    "192.168.1.181",
}

TURNSTILE_OUT_HOSTS = {
    "192.168.0.224",
    "192.168.0.222",
    "192.168.0.220",
    "192.168.1.180",
}


def _current_local_day() -> date:
    tz_local = timezone(timedelta(hours=5))
    return datetime.now(tz_local).date()


def _local_day_bounds(day: date) -> tuple[datetime, datetime]:
    tz_local = timezone(timedelta(hours=5))
    start_local = datetime(day.year, day.month, day.day, tzinfo=tz_local)
    end_local = start_local + timedelta(days=1)
    return start_local, end_local


def _esmo_result_rank(result_raw: str | None) -> int:
    value = (result_raw or "").strip().lower()
    if value == "passed":
        return 3
    if value in {"review", "manual_review", "ko'rik", "korik"}:
        return 2
    if value in {"failed", "fail", "rejected"}:
        return 1
    return 0


def _to_local_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    tz_local = timezone(timedelta(hours=5))
    return dt.astimezone(tz_local).replace(tzinfo=None)


def _latest_esmo_result_counts(
    db: Session,
    start_local_naive: datetime | None = None,
    end_local_naive: datetime | None = None,
) -> tuple[int, int, int]:
    query = (
        db.query(MedicalExam.employee_id, MedicalExam.result, MedicalExam.timestamp, MedicalExam.id, MedicalExam.esmo_id)
        .filter(MedicalExam.terminal_name.in_(get_allowed_esmo_terminal_names()))
    )
    if start_local_naive is not None:
        query = query.filter(MedicalExam.timestamp >= start_local_naive)
    if end_local_naive is not None:
        query = query.filter(MedicalExam.timestamp <= end_local_naive)

    rows = query.order_by(MedicalExam.timestamp.desc(), MedicalExam.esmo_id.desc().nullslast(), MedicalExam.id.desc()).all()

    latest_result_by_employee: dict[int, tuple[str, datetime, int, int, int]] = {}
    for employee_id, raw_result, ts, row_id, esmo_id in rows:
        esmo_key = int(esmo_id or 0)
        normalized = (raw_result or "").strip().lower()
        current = latest_result_by_employee.get(employee_id)
        if current is None:
            latest_result_by_employee[employee_id] = (normalized, ts, row_id, esmo_key, _esmo_result_rank(normalized))
            continue

        _current_result, current_ts, current_id, current_esmo_key, current_rank = current
        candidate_rank = _esmo_result_rank(normalized)
        should_replace = False
        if ts > current_ts:
            should_replace = True
        elif ts == current_ts:
            if esmo_key > current_esmo_key:
                should_replace = True
            elif esmo_key == current_esmo_key and candidate_rank > current_rank:
                should_replace = True
            elif esmo_key == current_esmo_key and candidate_rank == current_rank and row_id > current_id:
                should_replace = True

        if should_replace:
            latest_result_by_employee[employee_id] = (normalized, ts, row_id, esmo_key, candidate_rank)

    passed = 0
    failed = 0
    review = 0
    for result, _ts, _id, _esmo_key, _rank in latest_result_by_employee.values():
        if result == "passed":
            passed += 1
        elif result in {"review", "manual_review", "ko'rik", "korik"}:
            review += 1
        elif result in {"failed", "fail", "rejected"}:
            failed += 1

    return passed, failed, review


@router.get("/summary", response_model=ReportSummary)
def get_report_summary(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> ReportSummary:
    # Query to count all event types in one go
    counts_query = db.query(Event.event_type, func.count(Event.id))
    if date_from is not None:
        counts_query = counts_query.filter(Event.event_ts >= date_from)
    if date_to is not None:
        counts_query = counts_query.filter(Event.event_ts <= date_to)
    counts = counts_query.group_by(Event.event_type).all()
    
    mapping = {row[0]: row[1] for row in counts}
    
    # Blocked attempts (status REJECTED)
    blocked_query = db.query(func.count(Event.id)).filter(Event.status == EventStatus.REJECTED)
    if date_from is not None:
        blocked_query = blocked_query.filter(Event.event_ts >= date_from)
    if date_to is not None:
        blocked_query = blocked_query.filter(Event.event_ts <= date_to)
    blocked_count = blocked_query.scalar() or 0

    esmo_ok_latest, esmo_failed_latest, esmo_review_latest = _latest_esmo_result_counts(
        db=db,
        start_local_naive=_to_local_naive(date_from) if date_from is not None else None,
        end_local_naive=_to_local_naive(date_to) if date_to is not None else None,
    )

    return ReportSummary(
        turnstile_in=mapping.get(EventType.TURNSTILE_IN, 0),
        turnstile_out=mapping.get(EventType.TURNSTILE_OUT, 0),
        # Reports table has only OK/FAIL columns, so review is grouped into FAIL.
        esmo_ok=esmo_ok_latest,
        esmo_fail=esmo_failed_latest + esmo_review_latest,
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
            func.max(case((Event.event_type == EventType.TURNSTILE_IN, Event.event_ts), else_=None)).label("last_in"),
            func.max(case((Event.event_type.in_([EventType.TURNSTILE_OUT]), Event.event_ts), else_=None)).label("last_out"),
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
    day: date | None = Query(default=None, description="YYYY-MM-DD (optional, daily filter)"),
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

    rows_query = (
        db.query(Employee, subq.c.last_take, subq.c.last_return)
        .join(subq, subq.c.employee_id == Employee.id)
        .filter(subq.c.last_take.isnot(None))
        .filter((subq.c.last_return.is_(None)) | (subq.c.last_take > subq.c.last_return))
    )

    if day is not None:
        start, end = _local_day_bounds(day)
        rows_query = rows_query.filter(subq.c.last_take >= start, subq.c.last_take < end)

    rows = rows_query.all()

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

    events = (
        db.query(Event, Device.host)
        .join(Device, Device.id == Event.device_id)
        .filter(
            Event.status == EventStatus.ACCEPTED,
            Event.event_type.in_([EventType.TURNSTILE_IN, EventType.TURNSTILE_OUT]),
            Event.event_ts >= start,
            Event.event_ts < end,
            Device.host.in_(TURNSTILE_JOURNAL_HOSTS),
        )
        .order_by(Event.employee_id, Event.event_ts, Event.id)
        .all()
    )

    summary: dict[int, dict] = {}
    for ev, device_host in events:
        emp_id = ev.employee_id
        if emp_id not in summary:
            summary[emp_id] = {
                "last_in_today": None,
                "last_out_today": None,
                "is_inside": False,
                "has_in_today": False,
                "has_out_today": False,
            }

        entry = summary[emp_id]

        normalized_is_in: bool
        if device_host in TURNSTILE_IN_HOSTS:
            normalized_is_in = True
        elif device_host in TURNSTILE_OUT_HOSTS:
            normalized_is_in = False
        else:
            normalized_is_in = ev.event_type == EventType.TURNSTILE_IN

        if normalized_is_in:
            entry["has_in_today"] = True
            entry["last_in_today"] = ev.event_ts
            entry["is_inside"] = True
        else:
            entry["has_out_today"] = True
            entry["last_out_today"] = ev.event_ts
            entry["is_inside"] = False

    now = datetime.now(TZ)
    effective_now = now if now < end else end

    if not summary:
        return []

    employees = db.query(Employee).filter(Employee.id.in_(list(summary.keys()))).all()
    by_id = {emp.id: emp for emp in employees}

    result: list[MineWorkSummaryItem] = []
    for emp_id, data in summary.items():
        emp = by_id.get(emp_id)
        if not emp:
            continue

        last_in = data["last_in_today"]
        last_out = data["last_out_today"]

        # If currently inside, hide exit time in table.
        final_last_out = last_out if not data["is_inside"] else None

        session_minutes = 0
        if last_in:
            l_in = last_in if last_in.tzinfo is not None else last_in.replace(tzinfo=TZ)

            if data["is_inside"]:
                if effective_now > l_in:
                    session_minutes = int((effective_now - l_in).total_seconds() // 60)
            elif last_out:
                l_out = last_out if last_out.tzinfo is not None else last_out.replace(tzinfo=TZ)
                if l_out > l_in:
                    session_minutes = int((l_out - l_in).total_seconds() // 60)

        full_name = f"{emp.last_name} {emp.first_name} {emp.patronymic or ''}".strip()
        result.append(
            MineWorkSummaryItem(
                employee_id=emp.id,
                employee_no=emp.employee_no,
                full_name=full_name,
                total_minutes=max(session_minutes, 0),
                last_in=last_in,
                last_out=final_last_out,
                is_inside=data["is_inside"],
                entered_today=bool(data.get("has_in_today")),
                exited_today=bool(data.get("has_out_today")),
            )
        )
    return result


@router.get("/blocked-attempts", response_model=list[dict])
def blocked_attempts(
    day: date | None = Query(default=None, description="YYYY-MM-DD (optional, daily filter)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
    limit: int = Query(default=200, ge=1, le=2000),
) -> list[dict]:
    query = db.query(Event).filter(Event.status == EventStatus.REJECTED)
    if day is not None:
        start, end = _local_day_bounds(day)
        query = query.filter(Event.event_ts >= start, Event.event_ts < end)

    events = query.order_by(Event.event_ts.desc()).limit(limit).all()
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


@router.get("/blocked-attempts-count", response_model=int)
def blocked_attempts_count(
    day: date | None = Query(default=None, description="YYYY-MM-DD (optional, daily filter)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> int:
    if day is None:
        day = _current_local_day()
    start, end = _local_day_bounds(day)
    count = (
        db.query(func.count(Event.id))
        .filter(
            Event.status == EventStatus.REJECTED,
            Event.event_ts >= start,
            Event.event_ts < end,
        )
        .scalar()
    )
    return int(count or 0)


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


@router.get("/esmo-summary-24h", response_model=EsmoSummary24h)
def esmo_summary_24h(
    day: date | None = Query(default=None, description="YYYY-MM-DD (optional, local day)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> EsmoSummary24h:
    """
    Return ESMO results for the current local calendar day (Tashkent time).
    """
    if day is None:
        day = _current_local_day()

    tz_local = timezone(timedelta(hours=5))
    start_local = datetime(day.year, day.month, day.day, tzinfo=tz_local)
    end_local = start_local + timedelta(days=1)

    # MedicalExam timestamps are stored as local naive datetime.
    start_local_naive = start_local.replace(tzinfo=None)
    end_local_naive = end_local.replace(tzinfo=None)

    passed, failed, review = _latest_esmo_result_counts(
        db=db,
        start_local_naive=start_local_naive,
        end_local_naive=end_local_naive - timedelta(microseconds=1),
    )

    total = passed + failed + review
    return EsmoSummary24h(passed=passed, failed=failed, review=review, total=total)
