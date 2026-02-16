import os
import sys

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models.event import Event

def check_events():
    db = SessionLocal()
    try:
        events = db.query(Event).order_by(Event.received_ts.desc()).limit(5).all()
        print(f"Total events found: {len(events)}")
        for e in events:
            print(f"ID: {e.id}, Device: {e.device_id}, Status: {e.status}, Time: {e.received_ts}")
    finally:
        db.close()

if __name__ == "__main__":
    check_events()
