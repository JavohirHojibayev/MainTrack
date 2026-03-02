import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.audit import log_audit
from app.core.config import settings
from app.core.rbac import require_roles
from app.models.device import Device, DeviceType
from app.models.event import Event
from app.models.medical_exam import MedicalExam
from app.models.user import User
from app.schemas.device import DeviceCreate, DeviceDataStatusOut, DeviceOut, DevicePowerToggle, DeviceUpdate

router = APIRouter()

TURNSTILE_NAME_BY_HOST = {
    "192.168.1.181": "shaxta kirish",
    "192.168.1.180": "shaxta chiqish",
}


@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer"))) -> list[DeviceOut]:
    try:
        devices = db.query(Device).order_by(Device.id).all()
        updated = False
        for device in devices:
            host = (device.host or "").strip()
            forced_name = TURNSTILE_NAME_BY_HOST.get(host)
            if forced_name and device.name != forced_name:
                device.name = forced_name
                if device.location in {"shaxta kirish", "shaxta chiqish", "Kirish-4", "Kirish-5", None}:
                    device.location = forced_name
                updated = True
        if updated:
            db.commit()
            for device in devices:
                db.refresh(device)
        print(f"DEBUG: Found {len(devices)} devices")
        return devices
    except Exception as e:
        print(f"DEBUG: Error listing devices: {e}")
        raise


@router.get("/data-status", response_model=list[DeviceDataStatusOut])
def list_device_data_status(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> list[DeviceDataStatusOut]:
    devices = db.query(Device.id, Device.name, Device.device_type).all()

    event_last_rows = db.query(
        Event.device_id,
        func.max(Event.event_ts).label("last_data_at"),
    ).group_by(Event.device_id).all()
    event_last_map = {int(row.device_id): row.last_data_at for row in event_last_rows}

    esmo_exam_last_rows = db.query(
        MedicalExam.terminal_name,
        func.max(MedicalExam.timestamp).label("last_data_at"),
    ).filter(MedicalExam.terminal_name.isnot(None)).group_by(MedicalExam.terminal_name).all()
    esmo_exam_last_map = {str(row.terminal_name): row.last_data_at for row in esmo_exam_last_rows}

    result: list[DeviceDataStatusOut] = []
    for d in devices:
        if d.device_type == DeviceType.ESMO:
            last_data_at = esmo_exam_last_map.get(d.name)
        else:
            last_data_at = event_last_map.get(int(d.id))
        result.append(DeviceDataStatusOut(device_id=int(d.id), last_data_at=last_data_at))

    return result


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
        host=payload.host,
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


@router.post("/{device_id}/power", response_model=DeviceOut)
def toggle_device_power(
    device_id: int,
    payload: DevicePowerToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
) -> DeviceOut:
    if payload.password != settings.DEVICE_CONTROL_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid control password")

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_active = bool(payload.is_active)
    log_audit(
        db,
        current_user.id,
        "UPDATE",
        "device_power",
        str(device.id),
        {"is_active": device.is_active},
    )
    db.commit()
    db.refresh(device)
    return device
