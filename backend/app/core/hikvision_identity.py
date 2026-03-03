from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_external_id import EmployeeExternalID

HIKVISION_SYSTEM = "HIKVISION"
HIKVISION_MINE_SYSTEM = "HIKVISION_MINE"
MINE_HOSTS = {"192.168.1.180", "192.168.1.181"}


def normalize_external_id(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if raw.isdigit():
        stripped = raw.lstrip("0")
        return stripped or "0"
    return raw


def external_id_candidates(value: str | None) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    normalized = normalize_external_id(raw)
    if normalized and normalized != raw:
        return [raw, normalized]
    return [raw]


def external_system_for_host(host: str | None) -> str:
    return HIKVISION_MINE_SYSTEM if (host or "").strip() in MINE_HOSTS else HIKVISION_SYSTEM


def find_employee_by_external_id(
    db: Session,
    system: str,
    external_id: str | None,
) -> Employee | None:
    candidates = external_id_candidates(external_id)
    if not candidates:
        return None

    rows = (
        db.query(EmployeeExternalID)
        .filter(
            EmployeeExternalID.system == system,
            EmployeeExternalID.external_id.in_(candidates),
        )
        .all()
    )
    if not rows:
        return None

    by_external = {str(row.external_id): row for row in rows}
    for candidate in candidates:
        match = by_external.get(candidate)
        if not match:
            continue
        return db.query(Employee).filter(Employee.id == match.employee_id).first()
    return None


def upsert_employee_external_id(
    db: Session,
    employee_id: int,
    system: str,
    external_id: str | None,
) -> str:
    normalized = normalize_external_id(external_id)
    if not normalized:
        return "skipped_empty"

    by_external = (
        db.query(EmployeeExternalID)
        .filter(
            EmployeeExternalID.system == system,
            EmployeeExternalID.external_id == normalized,
        )
        .first()
    )
    if by_external and by_external.employee_id != employee_id:
        return "conflict_external_taken"

    by_employee = (
        db.query(EmployeeExternalID)
        .filter(
            EmployeeExternalID.system == system,
            EmployeeExternalID.employee_id == employee_id,
        )
        .first()
    )

    if by_employee:
        if by_employee.external_id == normalized:
            return "unchanged"
        by_employee.external_id = normalized
        return "updated"

    db.add(
        EmployeeExternalID(
            employee_id=employee_id,
            system=system,
            external_id=normalized,
        )
    )
    return "created"
