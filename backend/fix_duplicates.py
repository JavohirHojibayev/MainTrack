from app.db.session import SessionLocal
from app.models.event import Event
from sqlalchemy import func
from datetime import timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_duplicates():
    db = SessionLocal()
    try:
        logger.info("Starting duplicate cleanup...")
        
        # Fetch all events ordered by employee and time
        events = db.query(Event).order_by(Event.employee_id, Event.event_ts).all()
        
        to_delete = []
        count = 0
        
        if not events:
            logger.info("No events found.")
            return

        # Simple linear scan
        # We compare current event with the "last kept" event for the same employee
        last_kept = events[0]
        
        for current in events[1:]:
            # Check if same employee
            if current.employee_id == last_kept.employee_id:
                # Check if same type
                if current.event_type == last_kept.event_type:
                    # Check time difference (within 5 seconds)
                    diff = current.event_ts - last_kept.event_ts
                    if diff < timedelta(seconds=5):
                        # It's a duplicate
                        to_delete.append(current.id)
                        count += 1
                        continue # Skip updating last_kept
            
            # If not duplicate (or different employee/type), this becomes the new last_kept
            last_kept = current

        logger.info(f"Found {count} duplicate events to delete.")
        
        if to_delete:
            # Delete in chunks if necessary, but for now simple delete
            # db.query(Event).filter(Event.id.in_(to_delete)).delete(synchronize_session=False)
            # SQLite/Postgres limit handling might be needed for huge lists, but let's try direct first
            # Given potentially large number, let's loop
            
            chunk_size = 1000
            for i in range(0, len(to_delete), chunk_size):
                chunk = to_delete[i:i+chunk_size]
                db.query(Event).filter(Event.id.in_(chunk)).delete(synchronize_session=False)
                db.commit()
                logger.info(f"Deleted chunk {i}-{i+len(chunk)}")
            
            logger.info("Cleanup complete.")
        else:
            logger.info("No duplicates found.")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clean_duplicates()
