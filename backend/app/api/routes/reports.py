from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.rbac import require_roles
from app.core.esmo_poller import get_allowed_esmo_terminal_names
from app.models.device import Device, DeviceType
from app.models.employee import Employee
from app.models.employee_external_id import EmployeeExternalID
from app.models.user import User
from app.models.event import Event, EventStatus, EventType
from app.models.medical_exam import MedicalExam
from app.schemas.report import (
    EsmoSummary24h,
    InsideMineItem,
    LampSelfActionIn,
    LampSelfActionOut,
    LampSelfStatusItem,
    MineWorkSummaryItem,
    ReportSummary,
    ToolDebtItem,
)

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

MINE_TURNSTILE_HOSTS = {"192.168.1.180", "192.168.1.181"}

LAMP_TURNSTILE_EVENT_TYPES = (
    EventType.TURNSTILE_IN,
    EventType.TURNSTILE_OUT,
    EventType.MINE_IN,
    EventType.MINE_OUT,
)


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


def _normalize_esmo_result(result_raw: str | None) -> str:
    value = (result_raw or "").strip().lower()
    if value == "passed":
        return "passed"
    if value in {"review", "manual_review", "ko'rik", "korik"}:
        return "review"
    return "fail"


def _normalize_numeric_employee_no(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw.isdigit():
        return raw
    stripped = raw.lstrip("0")
    return stripped or "0"


def _format_employee_no(value: str | None, min_len: int = 8) -> str:
    normalized = _normalize_numeric_employee_no(value)
    if not normalized.isdigit():
        return normalized
    return normalized.zfill(min_len)


def _normalize_identity_key(value: str | None) -> str:
    return "".join(ch for ch in (value or "").strip().lower() if ch.isalnum())


def _employee_no_lookup_keys(value: str | None) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return []

    candidates = [raw]
    normalized = _normalize_numeric_employee_no(raw)
    if normalized and normalized not in candidates:
        candidates.append(normalized)
    formatted = _format_employee_no(raw)
    if formatted and formatted not in candidates:
        candidates.append(formatted)

    keys: list[str] = []
    for candidate in candidates:
        key = _normalize_identity_key(candidate)
        if key and key not in keys:
            keys.append(key)
    return keys


def _payload_employee_no(source_payload: dict | None) -> str:
    if not isinstance(source_payload, dict):
        return ""
    return str(source_payload.get("employeeNoString") or source_payload.get("cardNo") or "").strip()


def _latest_esmo_exam_today(db: Session, employee_id: int) -> MedicalExam | None:
    today = _current_local_day()
    start_local, end_local = _local_day_bounds(today)
    start_naive = start_local.replace(tzinfo=None)
    end_naive = end_local.replace(tzinfo=None)

    return (
        db.query(MedicalExam)
        .filter(
            MedicalExam.employee_id == employee_id,
            MedicalExam.terminal_name.in_(get_allowed_esmo_terminal_names()),
            MedicalExam.timestamp >= start_naive,
            MedicalExam.timestamp < end_naive,
        )
        .order_by(MedicalExam.timestamp.desc(), MedicalExam.esmo_id.desc().nullslast(), MedicalExam.id.desc())
        .first()
    )


def _is_preferred_esmo_exam(candidate: MedicalExam, current: MedicalExam) -> bool:
    """
    Prefer passed/review over fail regardless of timestamp.
    If same result rank, prefer newer timestamp/source id.
    """
    candidate_rank = _esmo_result_rank(candidate.result)
    current_rank = _esmo_result_rank(current.result)
    if candidate_rank != current_rank:
        return candidate_rank > current_rank

    if candidate.timestamp > current.timestamp:
        return True
    if candidate.timestamp < current.timestamp:
        return False

    candidate_esmo_id = int(candidate.esmo_id or 0)
    current_esmo_id = int(current.esmo_id or 0)
    if candidate_esmo_id > current_esmo_id:
        return True
    if candidate_esmo_id < current_esmo_id:
        return False

    return int(candidate.id or 0) > int(current.id or 0)


def _effective_esmo_exam_today(db: Session, employee_id: int) -> MedicalExam | None:
    today = _current_local_day()
    start_local, end_local = _local_day_bounds(today)
    start_naive = start_local.replace(tzinfo=None)
    end_naive = end_local.replace(tzinfo=None)

    rows = (
        db.query(MedicalExam)
        .filter(
            MedicalExam.employee_id == employee_id,
            MedicalExam.terminal_name.in_(get_allowed_esmo_terminal_names()),
            MedicalExam.timestamp >= start_naive,
            MedicalExam.timestamp < end_naive,
        )
        .order_by(MedicalExam.timestamp.desc(), MedicalExam.esmo_id.desc().nullslast(), MedicalExam.id.desc())
        .all()
    )

    selected: MedicalExam | None = None
    for exam in rows:
        if selected is None or _is_preferred_esmo_exam(exam, selected):
            selected = exam
    return selected


def _last_tool_take_return(db: Session, employee_id: int) -> tuple[datetime | None, datetime | None]:
    row = (
        db.query(
            func.max(case((and_(Event.event_type == EventType.TOOL_TAKE, Event.status == EventStatus.ACCEPTED), Event.event_ts), else_=None)).label("last_take"),
            func.max(case((and_(Event.event_type == EventType.TOOL_RETURN, Event.status == EventStatus.ACCEPTED), Event.event_ts), else_=None)).label("last_return"),
        )
        .filter(Event.employee_id == employee_id)
        .first()
    )
    if not row:
        return None, None
    return row[0], row[1]


def _resolve_lamp_device(db: Session) -> Device:
    preferred = (
        db.query(Device)
        .filter(Device.is_active.is_(True), Device.device_type == DeviceType.TOOL_FACE)
        .order_by(Device.id.asc())
        .first()
    )
    if preferred:
        return preferred

    named = (
        db.query(Device)
        .filter(
            Device.is_active.is_(True),
            (Device.name.ilike("%lamp%")) | (Device.name.ilike("%self%")) | (Device.device_code.ilike("%TOOL%")),
        )
        .order_by(Device.id.asc())
        .first()
    )
    if named:
        return named

    manual = db.query(Device).filter(Device.device_code == "LAMP_SELF_MANUAL").first()
    if manual:
        if not manual.is_active:
            manual.is_active = True
            db.flush()
        return manual

    manual = Device(
        name="Lamp & self-rescuer manual",
        device_code="LAMP_SELF_MANUAL",
        device_type=DeviceType.OTHER,
        location="Warehouse",
        api_key=f"lamp-self-{uuid4().hex}",
        is_active=True,
    )
    db.add(manual)
    db.flush()
    return manual


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
        candidate_rank = _esmo_result_rank(normalized)
        if current is None:
            latest_result_by_employee[employee_id] = (normalized, ts, row_id, esmo_key, candidate_rank)
            continue

        _current_result, current_ts, current_id, current_esmo_key, current_rank = current
        should_replace = False
        if candidate_rank > current_rank:
            should_replace = True
        elif candidate_rank < current_rank:
            should_replace = False
        elif ts > current_ts:
            should_replace = True
        elif ts == current_ts:
            if esmo_key > current_esmo_key:
                should_replace = True
            elif esmo_key == current_esmo_key and row_id > current_id:
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

    mine_counts_query = (
        db.query(Event.event_type, func.count(Event.id))
        .join(Device, Device.id == Event.device_id)
        .filter(
            Event.status == EventStatus.ACCEPTED,
            Device.device_type == DeviceType.MINE_FACE,
            Event.event_type.in_(LAMP_TURNSTILE_EVENT_TYPES),
        )
    )
    if date_from is not None:
        mine_counts_query = mine_counts_query.filter(Event.event_ts >= date_from)
    if date_to is not None:
        mine_counts_query = mine_counts_query.filter(Event.event_ts <= date_to)

    mine_rows = mine_counts_query.group_by(Event.event_type).all()
    mine_mapping = {event_type: count for event_type, count in mine_rows}
    mine_in_count = int(mine_mapping.get(EventType.MINE_IN, 0)) + int(mine_mapping.get(EventType.TURNSTILE_IN, 0))
    mine_out_count = int(mine_mapping.get(EventType.MINE_OUT, 0)) + int(mine_mapping.get(EventType.TURNSTILE_OUT, 0))
 
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
        mine_in=mine_in_count,
        mine_out=mine_out_count,
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


@router.get("/lamp-self-rescuer", response_model=list[LampSelfStatusItem])
def lamp_self_rescuer_status(
    start_date: date | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: date | None = Query(default=None, description="YYYY-MM-DD"),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> list[LampSelfStatusItem]:
    if start_date is None and end_date is None:
        today = _current_local_day()
        start_date = today
        end_date = today
    elif start_date is None:
        start_date = end_date
    elif end_date is None:
        end_date = start_date

    if end_date < start_date:
        start_date, end_date = end_date, start_date

    tz_local = timezone(timedelta(hours=5))
    start_local = datetime(start_date.year, start_date.month, start_date.day, tzinfo=tz_local)
    end_local = datetime(end_date.year, end_date.month, end_date.day, tzinfo=tz_local) + timedelta(days=1)

    start_local_naive = start_local.replace(tzinfo=None)
    end_local_naive = end_local.replace(tzinfo=None)

    exam_rows = (
        db.query(MedicalExam)
        .filter(
            MedicalExam.terminal_name.in_(get_allowed_esmo_terminal_names()),
            MedicalExam.timestamp >= start_local_naive,
            MedicalExam.timestamp < end_local_naive,
        )
        .order_by(MedicalExam.timestamp.desc(), MedicalExam.esmo_id.desc().nullslast(), MedicalExam.id.desc())
        .all()
    )

    latest_exam_by_employee: dict[int, MedicalExam] = {}
    for exam in exam_rows:
        current = latest_exam_by_employee.get(exam.employee_id)
        if current is None or _is_preferred_esmo_exam(exam, current):
            latest_exam_by_employee[exam.employee_id] = exam

    if not latest_exam_by_employee:
        return []

    employee_ids = list(latest_exam_by_employee.keys())
    employees = db.query(Employee).filter(Employee.id.in_(employee_ids)).all()
    employees_by_id = {emp.id: emp for emp in employees}

    mine_external_rows = (
        db.query(EmployeeExternalID.employee_id, EmployeeExternalID.external_id)
        .filter(
            EmployeeExternalID.system == "HIKVISION_MINE",
            EmployeeExternalID.employee_id.in_(employee_ids),
        )
        .all()
    )
    mine_external_by_employee: dict[int, str] = {
        int(employee_id): str(external_id or "").strip()
        for employee_id, external_id in mine_external_rows
        if str(external_id or "").strip()
    }

    turnstile_events = (
        db.query(
            Event.employee_id,
            Event.event_ts,
            Event.source_payload,
            Employee.employee_no,
            Employee.first_name,
            Employee.last_name,
            Employee.patronymic,
        )
        .join(Device, Device.id == Event.device_id)
        .join(Employee, Employee.id == Event.employee_id)
        .filter(
            Event.status == EventStatus.ACCEPTED,
            Event.event_type.in_(LAMP_TURNSTILE_EVENT_TYPES),
            Event.event_ts >= start_local,
            Event.event_ts < end_local,
            Device.host.in_(MINE_TURNSTILE_HOSTS),
        )
        .order_by(Event.event_ts.desc(), Event.id.desc())
        .all()
    )

    turnstile_by_employee_id: dict[int, datetime] = {}
    turnstile_by_employee_no: dict[str, datetime] = {}
    turnstile_by_full_name: dict[str, datetime] = {}
    for turnstile_employee_id, event_ts, source_payload, event_employee_no, first_name, last_name, patronymic in turnstile_events:
        current_by_id = turnstile_by_employee_id.get(turnstile_employee_id)
        if current_by_id is None or event_ts > current_by_id:
            turnstile_by_employee_id[turnstile_employee_id] = event_ts

        payload_no = _payload_employee_no(source_payload)
        for lookup_value in (event_employee_no, payload_no):
            for key in _employee_no_lookup_keys(lookup_value):
                current_by_no = turnstile_by_employee_no.get(key)
                if current_by_no is None or event_ts > current_by_no:
                    turnstile_by_employee_no[key] = event_ts

        event_full_name = f"{last_name} {first_name} {patronymic or ''}".strip()
        payload_name = ""
        if isinstance(source_payload, dict):
            payload_name = str(source_payload.get("name") or "").strip()

        for lookup_name in (event_full_name, payload_name):
            name_key = _normalize_identity_key(lookup_name)
            if not name_key:
                continue
            current_by_name = turnstile_by_full_name.get(name_key)
            if current_by_name is None or event_ts > current_by_name:
                turnstile_by_full_name[name_key] = event_ts

    tool_rows = (
        db.query(
            Event.employee_id,
            Event.event_type,
            Event.status,
            Event.event_ts,
            Event.reject_reason,
            Event.source_payload,
            Device.name,
        )
        .join(Device, Device.id == Event.device_id)
        .filter(
            Event.event_type.in_([EventType.TOOL_TAKE, EventType.TOOL_RETURN]),
            Event.employee_id.in_(employee_ids),
            Event.event_ts >= start_local,
            Event.event_ts < end_local,
        )
        .order_by(Event.employee_id, Event.event_ts, Event.id)
        .all()
    )

    last_take_by_employee: dict[int, datetime] = {}
    last_return_by_employee: dict[int, datetime] = {}
    last_rejected_take_by_employee: dict[int, datetime] = {}
    issuer_by_employee: dict[int, str] = {}
    for employee_id, event_type, event_status, event_ts, reject_reason, source_payload, device_name in tool_rows:
        if event_type == EventType.TOOL_TAKE and event_status == EventStatus.ACCEPTED:
            last_take_by_employee[employee_id] = event_ts
            actor_login = ""
            source_name = ""
            if isinstance(source_payload, dict):
                actor_login = str(
                    source_payload.get("actor_login")
                    or source_payload.get("issuer")
                    or source_payload.get("username")
                    or ""
                ).strip()
                source_name = str(source_payload.get("source") or "").strip().lower()
            if not actor_login and source_name == "ui":
                actor_login = "admin"
            issuer_by_employee[employee_id] = actor_login or (device_name or "").strip() or "System"
        elif event_type == EventType.TOOL_TAKE and event_status == EventStatus.REJECTED:
            reason = (reject_reason or "").strip().lower()
            if "already issued" in reason or "not returned" in reason:
                last_rejected_take_by_employee[employee_id] = event_ts
        elif event_type == EventType.TOOL_RETURN and event_status == EventStatus.ACCEPTED:
            last_return_by_employee[employee_id] = event_ts

    search_terms = [part.strip().lower() for part in (search or "").split() if part.strip()]

    result: list[LampSelfStatusItem] = []
    for employee_id, exam in sorted(
        latest_exam_by_employee.items(),
        key=lambda item: (item[1].timestamp, item[1].esmo_id or 0, item[1].id),
        reverse=True,
    ):
        employee = employees_by_id.get(employee_id)
        if employee is None:
            continue

        full_name = f"{employee.last_name} {employee.first_name} {employee.patronymic or ''}".strip()
        employee_no_raw = (employee.employee_no or "").strip()
        employee_no_haystack = employee_no_raw
        if employee_no_raw.isdigit():
            employee_no_haystack = f"{employee_no_raw} {_normalize_numeric_employee_no(employee_no_raw)} {_format_employee_no(employee_no_raw)}"
        haystack = f"{employee_no_haystack} {full_name}".lower()
        if search_terms and not all(term in haystack for term in search_terms):
            continue

        esmo_status = _normalize_esmo_result(exam.result)
        issued_at = last_take_by_employee.get(employee_id)
        returned_at = last_return_by_employee.get(employee_id)
        last_rejected_take = last_rejected_take_by_employee.get(employee_id)

        active_issue = bool(issued_at and (returned_at is None or issued_at > returned_at))
        if active_issue and last_rejected_take and issued_at and last_rejected_take >= issued_at:
            status = "FAIL"
            quantity = 1
        elif active_issue:
            status = "ISSUED"
            quantity = 1
        elif issued_at and returned_at and returned_at >= issued_at:
            status = "DONE"
            quantity = 0
        else:
            status = "NOT_ISSUED"
            quantity = 0

        turnstile_time = turnstile_by_employee_id.get(employee_id)
        if turnstile_time is None:
            no_candidates = [employee.employee_no, mine_external_by_employee.get(employee_id)]
            for candidate in no_candidates:
                if turnstile_time is not None:
                    break
                for key in _employee_no_lookup_keys(candidate):
                    ts = turnstile_by_employee_no.get(key)
                    if ts is not None:
                        turnstile_time = ts
                        break
        if turnstile_time is None:
            name_key = _normalize_identity_key(full_name)
            if name_key:
                turnstile_time = turnstile_by_full_name.get(name_key)

        result.append(
            LampSelfStatusItem(
                employee_id=employee.id,
                employee_no=employee.employee_no,
                full_name=full_name,
                turnstile_time=turnstile_time,
                esmo_time=exam.timestamp,
                esmo_status=esmo_status,
                tool_name="Lamp & self-rescuer",
                quantity=quantity,
                issued_at=issued_at,
                returned_at=returned_at,
                issuer=issuer_by_employee.get(employee_id),
                status=status,
            )
        )

    return result


@router.post("/lamp-self-rescuer/issue", response_model=LampSelfActionOut)
def issue_lamp_self_rescuer(
    payload: LampSelfActionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin", "admin", "dispatcher", "warehouse")),
) -> LampSelfActionOut:
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    if employee is None:
        return LampSelfActionOut(success=False, status="FAIL", message="Employee not found")

    latest_exam = _effective_esmo_exam_today(db, employee.id)
    if latest_exam is None:
        return LampSelfActionOut(success=False, status="FAIL", message="No ESMO exam today")

    latest_result = _normalize_esmo_result(latest_exam.result)
    if latest_result not in {"passed", "review"}:
        return LampSelfActionOut(success=False, status="FAIL", message="ESMO status is not passed/review")

    last_take, last_return = _last_tool_take_return(db, employee.id)
    has_active_issue = bool(last_take and (last_return is None or last_take > last_return))
    tool_device = _resolve_lamp_device(db)
    now_ts = datetime.now(timezone(timedelta(hours=5)))

    if has_active_issue:
        rejected = Event(
            device_id=tool_device.id,
            employee_id=employee.id,
            event_type=EventType.TOOL_TAKE,
            event_ts=now_ts,
            raw_id=f"ui-tool-take-reject:{uuid4().hex}",
            status=EventStatus.REJECTED,
            reject_reason="Already issued (not returned)",
            source_payload={
                "source": "ui",
                "action": "issue",
                "scope": "lamp_self",
                "actor_login": current_user.username,
            },
        )
        db.add(rejected)
        db.commit()
        db.refresh(rejected)
        return LampSelfActionOut(
            success=False,
            status="FAIL",
            message="Already issued, return first",
            event_id=rejected.id,
            event_ts=rejected.event_ts,
        )

    accepted = Event(
        device_id=tool_device.id,
        employee_id=employee.id,
        event_type=EventType.TOOL_TAKE,
        event_ts=now_ts,
        raw_id=f"ui-tool-take:{uuid4().hex}",
        status=EventStatus.ACCEPTED,
        reject_reason=None,
        source_payload={
            "source": "ui",
            "action": "issue",
            "scope": "lamp_self",
            "actor_login": current_user.username,
        },
    )
    db.add(accepted)
    db.commit()
    db.refresh(accepted)
    return LampSelfActionOut(
        success=True,
        status="ISSUED",
        message="Issued successfully",
        event_id=accepted.id,
        event_ts=accepted.event_ts,
    )


@router.post("/lamp-self-rescuer/return", response_model=LampSelfActionOut)
def return_lamp_self_rescuer(
    payload: LampSelfActionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin", "admin", "dispatcher", "warehouse")),
) -> LampSelfActionOut:
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    if employee is None:
        return LampSelfActionOut(success=False, status="FAIL", message="Employee not found")

    last_take, last_return = _last_tool_take_return(db, employee.id)
    has_active_issue = bool(last_take and (last_return is None or last_take > last_return))
    if not has_active_issue:
        return LampSelfActionOut(success=False, status="NOT_ISSUED", message="No active issue")

    tool_device = _resolve_lamp_device(db)
    now_ts = datetime.now(timezone(timedelta(hours=5)))
    accepted = Event(
        device_id=tool_device.id,
        employee_id=employee.id,
        event_type=EventType.TOOL_RETURN,
        event_ts=now_ts,
        raw_id=f"ui-tool-return:{uuid4().hex}",
        status=EventStatus.ACCEPTED,
        reject_reason=None,
        source_payload={
            "source": "ui",
            "action": "return",
            "scope": "lamp_self",
            "actor_login": current_user.username,
        },
    )
    db.add(accepted)
    db.commit()
    db.refresh(accepted)
    return LampSelfActionOut(
        success=True,
        status="DONE",
        message="Returned successfully",
        event_id=accepted.id,
        event_ts=accepted.event_ts,
    )


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
                "display_employee_no": "",
            }

        entry = summary[emp_id]
        payload_no = _payload_employee_no(ev.source_payload)
        if payload_no:
            entry["display_employee_no"] = payload_no

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
                employee_no=(data.get("display_employee_no") or emp.employee_no),
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
