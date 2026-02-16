from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.audit import log_audit
from app.core.rbac import require_roles
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate

router = APIRouter()


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db), _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer"))) -> list[EmployeeOut]:
    return db.query(Employee).order_by(Employee.id).all()


@router.post("", response_model=EmployeeOut)
def create_employee(
    payload: EmployeeCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("superadmin", "admin"))
) -> EmployeeOut:
    existing = db.query(Employee).filter(Employee.employee_no == payload.employee_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee number already exists")
    employee = Employee(**payload.dict())
    db.add(employee)
    log_audit(db, current_user.id, "CREATE", "employee", None, {"employee_no": employee.employee_no})
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer"))
) -> EmployeeOut:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin", "admin")),
) -> EmployeeOut:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(employee, key, value)
    log_audit(db, current_user.id, "UPDATE", "employee", str(employee.id), payload.dict(exclude_unset=True))
    db.commit()
    db.refresh(employee)
    return employee
