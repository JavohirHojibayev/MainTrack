from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.core import deps
from app.models.employee import Employee
from app.models.employee_external_id import EmployeeExternalID
from app.models.medical_exam import MedicalExam
from app.models.event import Event
from app.core.esmo_poller import get_allowed_esmo_terminal_names, poll_esmo_once
from app.schemas.medical_exam import MedicalExamRead

router = APIRouter()
ESMO_SYSTEM = "ESMO"

def _is_newer_exam(candidate: MedicalExam, current: MedicalExam) -> bool:
    cand_ts = candidate.timestamp
    curr_ts = current.timestamp
    if cand_ts > curr_ts:
        return True
    if cand_ts < curr_ts:
        return False

    # Same timestamp: prefer larger ESMO source id if present.
    cand_esmo_id = candidate.esmo_id or 0
    curr_esmo_id = current.esmo_id or 0
    if cand_esmo_id > curr_esmo_id:
        return True
    if cand_esmo_id < curr_esmo_id:
        return False

    # Same timestamp/source id: keep deterministic latest inserted row.
    return candidate.id > current.id


def _local_day_bounds(day_value: date) -> tuple[datetime, datetime]:
    # MedicalExam.timestamp is stored as local naive datetime (ESMO local time).
    start_local = datetime(day_value.year, day_value.month, day_value.day)
    end_local = start_local + timedelta(days=1)
    return start_local, end_local


def _ensure_esmo_enabled() -> None:
    from app.core.config import settings

    if not settings.ESMO_ENABLED:
        raise HTTPException(status_code=503, detail="ESMO integration is disabled")


def _fetch_esmo_employees_from_portal(max_pages: int) -> tuple[list[dict], str | None]:
    from app.core.config import settings
    from app.core.esmo_client import EsmoClient

    _ensure_esmo_enabled()
    client = EsmoClient(
        base_url=settings.ESMO_BASE_URL,
        username=settings.ESMO_USER,
        password=settings.ESMO_PASS,
        timeout=settings.ESMO_REQUEST_TIMEOUT,
        login_retries=settings.ESMO_LOGIN_RETRIES,
        employee_max_pages=max_pages,
    )
    employees = client.fetch_employees()
    return employees, client.last_error


def _split_full_name(full_name: str) -> tuple[str, str, str | None]:
    parts = [p for p in full_name.split() if p]
    if not parts:
        return "Unknown", "", None
    last_name = parts[0]
    first_name = parts[1] if len(parts) > 1 else ""
    patronymic = " ".join(parts[2:]) if len(parts) > 2 else None
    return last_name, first_name, patronymic


def _find_employee_for_esmo(db: Session, pass_id: str, full_name: str) -> Employee | None:
    if pass_id:
        ext = (
            db.query(EmployeeExternalID)
            .filter(
                EmployeeExternalID.system == ESMO_SYSTEM,
                EmployeeExternalID.external_id == pass_id,
            )
            .first()
        )
        if ext:
            return db.query(Employee).filter(Employee.id == ext.employee_id).first()

        by_no = db.query(Employee).filter(Employee.employee_no == pass_id).first()
        if by_no:
            return by_no

    if full_name:
        last_name, first_name, _ = _split_full_name(full_name)
        if first_name:
            by_name = (
                db.query(Employee)
                .filter(
                    Employee.last_name.ilike(f"%{last_name}%"),
                    Employee.first_name.ilike(f"%{first_name}%"),
                )
                .first()
            )
            if by_name:
                return by_name

    return None


def _apply_exam_search(query, search: str):
    terms = [part.strip() for part in search.split() if part.strip()]
    if not terms:
        return query

    predicates = []
    for term in terms:
        q = f"%{term}%"
        predicates.append(
            or_(
                MedicalExam.employee.has(Employee.employee_no.ilike(q)),
                MedicalExam.employee.has(Employee.first_name.ilike(q)),
                MedicalExam.employee.has(Employee.last_name.ilike(q)),
                MedicalExam.employee.has(Employee.patronymic.ilike(q)),
                MedicalExam.terminal_name.ilike(q),
            )
        )

    return query.filter(and_(*predicates))


def _compose_employee_full_name(exam: MedicalExam, payload_name: str | None) -> str:
    if payload_name and payload_name.strip():
        return payload_name.strip()
    if exam.employee:
        return f"{exam.employee.last_name} {exam.employee.first_name} {exam.employee.patronymic or ''}".strip()
    return f"ID: {exam.employee_id}"


def _serialize_medical_exams(db: Session, rows: list[MedicalExam]) -> list[MedicalExamRead]:
    esmo_ids = [int(exam.esmo_id) for exam in rows if exam.esmo_id is not None]
    payload_name_by_esmo_id: dict[int, str] = {}
    if esmo_ids:
        raw_ids = [f"esmo:{esmo_id}" for esmo_id in esmo_ids]
        event_rows = (
            db.query(Event.raw_id, Event.source_payload)
            .filter(Event.raw_id.in_(raw_ids))
            .all()
        )
        for raw_id, payload in event_rows:
            if not raw_id:
                continue
            try:
                esmo_id = int(str(raw_id).split(":", 1)[1])
            except Exception:
                continue
            if isinstance(payload, dict):
                full_name = (payload.get("employee_name") or "").strip()
                if full_name:
                    payload_name_by_esmo_id[esmo_id] = full_name

    out: list[MedicalExamRead] = []
    for exam in rows:
        item = MedicalExamRead.model_validate(exam, from_attributes=True)
        payload_name = payload_name_by_esmo_id.get(int(exam.esmo_id)) if exam.esmo_id is not None else None
        item.employee_full_name = _compose_employee_full_name(exam, payload_name)
        out.append(item)
    return out


def _list_esmo_employees_from_db(db: Session) -> list[dict]:
    rows = (
        db.query(EmployeeExternalID, Employee)
        .join(Employee, Employee.id == EmployeeExternalID.employee_id)
        .filter(EmployeeExternalID.system == ESMO_SYSTEM)
        .order_by(Employee.last_name, Employee.first_name, Employee.id)
        .all()
    )

    result: list[dict] = []
    for ext, emp in rows:
        full_name = f"{emp.last_name} {emp.first_name} {emp.patronymic or ''}".strip()
        pass_id = (ext.external_id or "").strip()
        result.append(
            {
                "id": pass_id or f"emp-{emp.id}",
                "pass_id": pass_id,
                "full_name": full_name,
                "organization": "",
                "department": emp.department or "",
                "position": emp.position or "",
            }
        )
    return result

@router.get("/exams", response_model=list[MedicalExamRead])
def get_medical_exams(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = None,
    result: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    latest_per_employee: bool = Query(default=False),
):
    """
    Get list of medical exams.
    """
    query = (
        db.query(MedicalExam)
        .options(joinedload(MedicalExam.employee))
        .filter(MedicalExam.terminal_name.in_(get_allowed_esmo_terminal_names()))
    )
    
    if employee_id:
        query = query.filter(MedicalExam.employee_id == employee_id)
    if result:
        query = query.filter(MedicalExam.result == result)
    if start_date:
        start_local, _ = _local_day_bounds(start_date)
        query = query.filter(MedicalExam.timestamp >= start_local)
    if end_date:
        _, end_local = _local_day_bounds(end_date)
        query = query.filter(MedicalExam.timestamp < end_local)
    if search:
        query = _apply_exam_search(query, search)
        
    # Order by newest first
    query = query.order_by(MedicalExam.timestamp.desc(), MedicalExam.id.desc())

    if latest_per_employee:
        all_rows = query.all()
        latest_by_employee: dict[int, MedicalExam] = {}
        for exam in all_rows:
            current = latest_by_employee.get(exam.employee_id)
            if current is None or _is_newer_exam(exam, current):
                latest_by_employee[exam.employee_id] = exam
        deduped_rows = sorted(
            latest_by_employee.values(),
            key=lambda item: (item.timestamp, item.esmo_id or 0, item.id),
            reverse=True,
        )
        paged_rows = deduped_rows[skip : skip + limit]
        return _serialize_medical_exams(db, paged_rows)

    rows = query.offset(skip).limit(limit).all()
    return _serialize_medical_exams(db, rows)

@router.get("/stats")
def get_medical_stats(
    db: Session = Depends(deps.get_db),
    target_date: date | None = Query(default=None)
):
    """
    Get simple statistics for a specific date (default today).
    """
    if target_date is None:
        target_date = datetime.now(timezone(timedelta(hours=5))).date()

    start_local, end_local = _local_day_bounds(target_date)
    
    query = db.query(MedicalExam).filter(
        MedicalExam.terminal_name.in_(get_allowed_esmo_terminal_names()),
        MedicalExam.timestamp >= start_local,
        MedicalExam.timestamp < end_local
    )
    
    total = query.count()
    passed = query.filter(MedicalExam.result == 'passed').count()
    failed = query.filter(MedicalExam.result == 'failed').count()
    
    return {
        "date": target_date,
        "total": total,
        "passed": passed,
        "failed": failed
    }

@router.post("/sync-exams")
def sync_esmo_exams():
    """
    Manually trigger ESMO medical exam synchronization.
    """
    _ensure_esmo_enabled()
    count = poll_esmo_once()
    return {"status": "ok", "new_exams_count": count}

@router.get("/esmo-employees")
def get_esmo_employees(db: Session = Depends(deps.get_db)):
    """
    Get the full list of employees from the ESMO portal.
    """
    from app.core.config import settings

    employees: list[dict] = []
    err: str | None = None
    try:
        employees, err = _fetch_esmo_employees_from_portal(settings.ESMO_EMPLOYEE_SYNC_PAGES)
    except HTTPException as exc:
        err = str(exc.detail) if exc.detail else str(exc)

    if employees:
        # Map for DataGrid (ensure 'id' exists)
        return [{**emp, "id": emp["pass_id"] or i} for i, emp in enumerate(employees)]

    # Fallback: return locally linked ESMO employees if portal is unavailable/empty.
    cached = _list_esmo_employees_from_db(db)
    if cached:
        return cached

    if err:
        raise HTTPException(status_code=502, detail=err)

    return []

@router.post("/sync-employees")
def sync_esmo_employees(db: Session = Depends(deps.get_db)):
    """
    Synchronize ESMO employees and link them to MineTrack employees.
    - Creates missing employees when possible (requires pass_id).
    - Ensures EmployeeExternalID(system='ESMO') mapping exists.
    """
    from app.core.config import settings

    employees, err = _fetch_esmo_employees_from_portal(settings.ESMO_EMPLOYEE_SYNC_PAGES)
    if not employees and err:
        raise HTTPException(status_code=502, detail=err)

    for emp in employees:
        pass_id = (emp.get("pass_id") or "").strip()
        full_name = (emp.get("full_name") or "").strip()
        department = (emp.get("department") or "").strip()
        position = (emp.get("position") or "").strip()

        employee = _find_employee_for_esmo(db, pass_id, full_name)

        if employee is None:
            if not pass_id:
                continue
            last_name, first_name, patronymic = _split_full_name(full_name)
            employee = Employee(
                employee_no=pass_id,
                first_name=first_name,
                last_name=last_name,
                patronymic=patronymic,
                department=department or None,
                position=position or None,
                is_active=True,
            )
            db.add(employee)
            db.flush()
        else:
            # Backfill optional profile fields if MineTrack side is empty.
            last_name, first_name, patronymic = _split_full_name(full_name)
            if patronymic and not (employee.patronymic or "").strip():
                employee.patronymic = patronymic
            if last_name and (
                not (employee.last_name or "").strip()
                or (employee.last_name or "").strip().lower() in {"unknown", "-"}
            ):
                employee.last_name = last_name
            if first_name and not (employee.first_name or "").strip():
                employee.first_name = first_name
            if department and not employee.department:
                employee.department = department
            if position and not employee.position:
                employee.position = position

        if not pass_id:
            continue

        ext_by_pass = (
            db.query(EmployeeExternalID)
            .filter(
                EmployeeExternalID.system == ESMO_SYSTEM,
                EmployeeExternalID.external_id == pass_id,
            )
            .first()
        )
        if ext_by_pass and ext_by_pass.employee_id != employee.id:
            # Conflicting link: pass_id already mapped to another employee.
            continue

        ext_by_employee = (
            db.query(EmployeeExternalID)
            .filter(
                EmployeeExternalID.system == ESMO_SYSTEM,
                EmployeeExternalID.employee_id == employee.id,
            )
            .first()
        )

        if ext_by_employee:
            if ext_by_employee.external_id != pass_id:
                ext_by_employee.external_id = pass_id
        elif not ext_by_pass:
            db.add(
                EmployeeExternalID(
                    employee_id=employee.id,
                    system=ESMO_SYSTEM,
                    external_id=pass_id,
                )
            )

    db.commit()
    return [{**emp, "id": emp["pass_id"] or i} for i, emp in enumerate(employees)]
