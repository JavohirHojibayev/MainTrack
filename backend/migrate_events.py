"""Migrate MINE_IN/MINE_OUT events to TURNSTILE_IN/TURNSTILE_OUT for factory turnstiles."""
from app.db.session import SessionLocal
from app.models.event import Event, EventType

db = SessionLocal()

mine_in = db.query(Event).filter(Event.event_type == EventType.MINE_IN).count()
mine_out = db.query(Event).filter(Event.event_type == EventType.MINE_OUT).count()
print(f"Before: MINE_IN={mine_in}, MINE_OUT={mine_out}")

# Update MINE_IN -> TURNSTILE_IN
db.query(Event).filter(Event.event_type == EventType.MINE_IN).update(
    {Event.event_type: EventType.TURNSTILE_IN}, synchronize_session=False
)

# Update MINE_OUT -> TURNSTILE_OUT
db.query(Event).filter(Event.event_type == EventType.MINE_OUT).update(
    {Event.event_type: EventType.TURNSTILE_OUT}, synchronize_session=False
)

db.commit()

turnstile_in = db.query(Event).filter(Event.event_type == EventType.TURNSTILE_IN).count()
turnstile_out = db.query(Event).filter(Event.event_type == EventType.TURNSTILE_OUT).count()
print(f"After: TURNSTILE_IN={turnstile_in}, TURNSTILE_OUT={turnstile_out}")

db.close()
print("Migration complete!")
