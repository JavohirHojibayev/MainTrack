from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core import deps
from app.models.employee import Employee
from app.models.employee_external_id import EmployeeExternalID
from app.models.medical_exam import MedicalExam
from app.core.esmo_poller import get_allowed_esmo_terminal_names, poll_esmo_once
from app.schemas.medical_exam import MedicalExamRead

router = APIRouter()
ESMO_SYSTEM = "ESMO"


def _local_day_bounds_utc(day_value: date) -> tuple[datetime, datetime]:
    tz_local = timezone(timedelta(hours=5))
    start_local = datetime(day_value.year, day_value.month, day_value.day, tzinfo=tz_local)
    end_local = start_local + timedelta(days=1)
    # Stored timestamps are UTC-naive in DB; compare with naive UTC bounds.
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


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
        start_utc, _ = _local_day_bounds_utc(start_date)
        query = query.filter(MedicalExam.timestamp >= start_utc)
    if end_date:
        _, end_utc = _local_day_bounds_utc(end_date)
        query = query.filter(MedicalExam.timestamp < end_utc)
    if search:
        q = f"%{search.strip()}%"
        query = query.join(Employee, isouter=True).filter(
            or_(
                Employee.employee_no.ilike(q),
                Employee.first_name.ilike(q),
                Employee.last_name.ilike(q),
                Employee.patronymic.ilike(q),
                MedicalExam.terminal_name.ilike(q),
            )
        )
        
    # Order by newest first
    query = query.order_by(MedicalExam.timestamp.desc())
    
    return query.offset(skip).limit(limit).all()

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

    start_utc, end_utc = _local_day_bounds_utc(target_date)
    
    query = db.query(MedicalExam).filter(
        MedicalExam.terminal_name.in_(get_allowed_esmo_terminal_names()),
        MedicalExam.timestamp >= start_utc,
        MedicalExam.timestamp < end_utc
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
