from sqlalchemy import text
from app.db.session import engine

def migrate():
    with engine.connect() as conn:
        print("Adding 'host' and 'last_seen' columns to 'devices' table...")
        
        # Add host column if it doesn't exist
        try:
            conn.execute(text("ALTER TABLE minetrack.devices ADD COLUMN host VARCHAR(255)"))
            print("Added 'host' column.")
        except Exception as e:
            print(f"Host column might already exist: {e}")
            
        # Add last_seen column if it doesn't exist
        try:
            conn.execute(text("ALTER TABLE minetrack.devices ADD COLUMN last_seen TIMESTAMP WITH TIME ZONE"))
            print("Added 'last_seen' column.")
        except Exception as e:
            print(f"Last_seen column might already exist: {e}")
            
        conn.commit()
        
        # Populate host from device_code if empty
        print("Populating 'host' field from 'device_code'...")
        res = conn.execute(text("SELECT id, device_code FROM minetrack.devices WHERE host IS NULL"))
        rows = res.fetchall()
        
        for row in rows:
            device_id, code = row
            # If code is like HIK_192_168_0_221 -> 192.168.0.221
            host = None
            if "_" in code:
                parts = code.split("_")
                ip_parts = [p for p in parts if p.replace(".", "").isdigit() or (p.isdigit() and int(p) <= 255)]
                if len(ip_parts) >= 1:
                    # In this specific case, 192_168_0_221 is split by _
                    # Let's try to rejoin the last 4 parts if they are digits
                    last_parts = parts[-4:]
                    if all(p.isdigit() for p in last_parts):
                        host = ".".join(last_parts)
            
            if not host and "." in code: # Maybe it's already an IP or has one
                 import re
                 match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', code)
                 if match:
                     host = match.group(1)
            
            if host:
                conn.execute(text("UPDATE minetrack.devices SET host = :host WHERE id = :id"), {"host": host, "id": device_id})
                print(f"Updated device {device_id} with host {host}")
        
        conn.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
