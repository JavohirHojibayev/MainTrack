
from app.db.session import SessionLocal
from app.models.device import Device
import sys

db = SessionLocal()
device = db.query(Device).filter(Device.host == "192.168.0.3").first()

if device:
    print(f"Found device: {device.name} ({device.device_code})")
    device.name = "Admin Terminal"
    device.device_code = "ADMIN_PC"
    device.location = "Server Room"
    db.commit()
    print("Device renamed to 'Admin Terminal' (ADMIN_PC)")
else:
    print("Device with host '192.168.0.3' not found.")

db.close()
