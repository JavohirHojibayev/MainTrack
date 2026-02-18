import sys
import os

# Ensure we can find the app module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.device import Device

# Mapping based on user request and iVMS
DEVICE_IP_MAP = {
    "192.168.0.223": {"name": "Kirish-1"},
    "192.168.0.221": {"name": "Kirish-2"},
    "192.168.0.219": {"name": "Kirish-3"},
    "192.168.0.224": {"name": "Chiqish-1"},
    "192.168.0.222": {"name": "Chiqish-2"},
    "192.168.0.220": {"name": "Chiqish-3"},
}

def fix_device_names():
    db = SessionLocal()
    try:
        print("Starting device name fix...")
        updated = 0
        
        for ip, config in DEVICE_IP_MAP.items():
            mapped_name = config["name"]
            
            # Find device by IP (host)
            device = db.query(Device).filter(Device.host == ip).first()
            
            if device:
                print(f"Checking {ip} (Current: {device.name})...")
                if device.name != mapped_name:
                    print(f"  -> Updating to {mapped_name}")
                    device.name = mapped_name
                    device.location = mapped_name 
                    updated += 1
                else:
                    print(f"  -> OK")
            else:
                print(f"Warning: Device with IP {ip} not found in DB.")

        if updated > 0:
            db.commit()
            print(f"Successfully updated {updated} devices.")
        else:
            print("No devices needed updating.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_device_names()
