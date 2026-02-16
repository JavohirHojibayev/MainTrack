import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.audit import log_audit
from app.core.rbac import require_roles
from app.models.device import Device
from app.models.user import User
from app.schemas.device import DeviceCreate, DeviceOut, DeviceUpdate

router = APIRouter()


@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer"))) -> list[DeviceOut]:
    return db.query(Device).order_by(Device.id).all()


@router.post("", response_model=DeviceOut)
def create_device(
    payload: DeviceCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("superadmin", "admin"))
) -> DeviceOut:
    existing = db.query(Device).filter(Device.device_code == payload.device_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device code already exists")
    api_key = payload.api_key or secrets.token_urlsafe(32)
    device = Device(
        name=payload.name,
        device_code=payload.device_code,
        device_type=payload.device_type,
        location=payload.location,
        api_key=api_key,
    )
    db.add(device)
    log_audit(db, current_user.id, "CREATE", "device", None, {"device_code": device.device_code})
    db.commit()
    db.refresh(device)
    return device


@router.patch("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin", "admin")),
) -> DeviceOut:
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(device, key, value)
    log_audit(db, current_user.id, "UPDATE", "device", str(device.id), payload.dict(exclude_unset=True))
    db.commit()
    db.refresh(device)
    return device
