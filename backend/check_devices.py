
from app.db.session import SessionLocal
from app.models.device import Device

db = SessionLocal()
devices = db.query(Device).all()
print(f"Total devices: {len(devices)}")
for d in devices:
    print(f" - {d.name} ({d.host}) Type: {d.device_type}")
db.close()
