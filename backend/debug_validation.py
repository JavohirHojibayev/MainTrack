
from app.db.session import SessionLocal
from app.models.device import Device
from app.schemas.device import DeviceOut
import sys

db = SessionLocal()
devices = db.query(Device).all()

print(f"Checking {len(devices)} devices...")

for d in devices:
    try:
        DeviceOut.model_validate(d)
        print(f"Device {d.id} OK")
    except Exception as e:
        print(f"Device {d.id} FAILED: {e}")
        # Print attributes to see what's wrong
        print(f"  Name: {d.name}")
        print(f"  Type: {d.device_type} ({type(d.device_type)})")
        print(f"  Host: {d.host}")
        print(f"  Last Seen: {d.last_seen}")

db.close()
