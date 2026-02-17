from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.deps import get_db
from app.core.audit import log_audit
from app.core.rbac import require_roles
from app.models.device import Device
from app.models.employee import Employee
from app.models.employee_external_id import EmployeeExternalID
from app.models.event import Event, EventStatus, EventType
from app.schemas.event import EventIngestRequest, EventOut, EventResult

router = APIRouter()


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _find_employee(db: Session, employee_no: str | None, external_system: str | None, external_id: str | None) -> Employee | None:
    if employee_no:
        return db.query(Employee).filter(Employee.employee_no == employee_no).first()
    if external_system and external_id:
        return (
            db.query(Employee)
            .join(EmployeeExternalID, EmployeeExternalID.employee_id == Employee.id)
            .filter(EmployeeExternalID.system == external_system, EmployeeExternalID.external_id == external_id)
            .first()
        )
    return None


def _has_recent_esmo_ok(db: Session, employee_id: int, event_ts: datetime) -> bool:
    window_start = event_ts - timedelta(hours=settings.ESMO_OK_WINDOW_HOURS)
    exists = (
        db.query(Event)
        .filter(
            Event.employee_id == employee_id,
            Event.event_type == EventType.ESMO_OK,
            Event.status == EventStatus.ACCEPTED,
            Event.event_ts >= window_start,
            Event.event_ts <= event_ts,
        )
        .first()
    )
    return exists is not None


@router.post("/ingest", response_model=list[EventResult])
def ingest_events(
    payload: EventIngestRequest,
    db: Session = Depends(get_db),
    api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> list[EventResult]:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    # 1. Validate Device via API Key
    device_by_key = db.query(Device).filter(Device.api_key == api_key, Device.is_active.is_(True)).first()
    if not device_by_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    current_device_id = device_by_key.id
    current_device_code = device_by_key.device_code

    # 2. Pre-fetch Data for Bulk Processing
    # Collect criteria
    employee_nos = {e.employee_no for e in payload.events if e.employee_no}
    external_ids = [(e.external_system, e.external_id) for e in payload.events if e.external_system and e.external_id]
    
    # 2a. Fetch Employees by Employee No
    employees_by_no: dict[str, Employee] = {}
    if employee_nos:
        emps = db.query(Employee).filter(Employee.employee_no.in_(employee_nos)).all()
        for e in emps:
            employees_by_no[e.employee_no] = e
            
    # 2b. Fetch Employees by External ID
    employees_by_ext: dict[tuple[str, str], Employee] = {}
    if external_ids:
        # Using tuple comparison for efficient querying
        from sqlalchemy import tuple_
        # chunks of external_ids if too many? For now assume reasonable batch size
        unique_ext_ids = list(set(external_ids)) # Remove duplicates
        if unique_ext_ids:
            results = (
                db.query(Employee, EmployeeExternalID.system, EmployeeExternalID.external_id)
                .join(EmployeeExternalID, EmployeeExternalID.employee_id == Employee.id)
                .filter(tuple_(EmployeeExternalID.system, EmployeeExternalID.external_id).in_(unique_ext_ids))
                .all()
            )
            for emp, sys, ext in results:
                employees_by_ext[(sys, ext)] = emp

    # Helper to resolve employee
    def get_employee(item) -> Employee | None:
        if item.employee_no:
            return employees_by_no.get(item.employee_no)
        if item.external_system and item.external_id:
            return employees_by_ext.get((item.external_system, item.external_id))
        return None

    # 3. Check for Duplicates
    raw_ids = [e.raw_id for e in payload.events]
    existing_events = (
        db.query(Event.raw_id, Event.id, Event.reject_reason)
        .filter(Event.device_id == current_device_id, Event.raw_id.in_(raw_ids))
        .all()
    )
    existing_map = {r.raw_id: r for r in existing_events}

    # 4. Prepare for ESMO Checks
    # We need to check ESMO_OK for MINE_IN and TOOL_TAKE events
    events_needing_esmo = []
    
    # Pre-process loop to classify events
    processed_items = [] # list of (item, employee, status, reason)
    
    for item in payload.events:
        # Device mismatch check
        if item.device_code != current_device_code:
            processed_items.append((item, None, "REJECTED", "API key/device mismatch"))
            continue

        # Duplicate check
        if item.raw_id in existing_map:
            dup = existing_map[item.raw_id]
            # Use specific status DUPLICATE to inform client
            # But return type expects EventResult which has status string
            processed_items.append((item, None, "DUPLICATE", dup.reject_reason)) 
            continue

        emp = get_employee(item)
        if not emp:
            processed_items.append((item, None, "REJECTED", "Employee not found"))
            continue

        event_ts = _ensure_utc(item.event_ts)
        
        # If checks needed
        if item.event_type in {EventType.MINE_IN, EventType.TOOL_TAKE}:
            events_needing_esmo.append((item, emp, event_ts))
            # Status determination deferred
            processed_items.append((item, emp, "PENDING", None))
        else:
            processed_items.append((item, emp, "ACCEPTED", None))

    # 5. Bulk ESMO Check
    esmo_ok_map: dict[int, list[datetime]] = {}
    if events_needing_esmo:
        emp_ids = {e.id for _, e, _ in events_needing_esmo}
        min_ts = min(ts for _, _, ts in events_needing_esmo)
        # Fetch window: min event time - window hours
        window_start = min_ts - timedelta(hours=settings.ESMO_OK_WINDOW_HOURS)
        
        esmo_logs = (
            db.query(Event.employee_id, Event.event_ts)
            .filter(
                Event.employee_id.in_(emp_ids),
                Event.event_type == EventType.ESMO_OK,
                Event.status == EventStatus.ACCEPTED,
                Event.event_ts >= window_start
            )
            .all()
        )
        
        for eid, ts in esmo_logs:
            if eid not in esmo_ok_map:
                esmo_ok_map[eid] = []
            esmo_ok_map[eid].append(ts)
            
        # Sort timestamps for binary search if needed, but linear scan is fine for small lists
        for eid in esmo_ok_map:
            esmo_ok_map[eid].sort()

    # 6. Finalize Status and Create Objects
    new_events = []
    results = []
    
    # We need to map back processed_items to results order? 
    # The processed_items list corresponds to payload.events 1-to-1? 
    # No, we skipped some logic flow.
    # Actually, processed_items is built in order of payload.events.
    # But wait, `events_needing_esmo` are also in `processed_items` with "PENDING".
    
    # Let's re-iterate processed_items and update "PENDING" ones
    final_events_to_insert = []
    
    # Map raw_id to its duplicate/error result if any, to avoid re-looping?
    # Better: iterate processed_items
    
    for item, emp, status, reason in processed_items:
        if status == "DUPLICATE":
            existing = existing_map[item.raw_id]
            results.append(EventResult(raw_id=item.raw_id, status="DUPLICATE", event_id=existing.id, reject_reason=existing.reject_reason))
            continue
            
        if status == "REJECTED":
            results.append(EventResult(raw_id=item.raw_id, status=status, reject_reason=reason))
            continue
            
        # If PENDING, do the check
        if status == "PENDING":
            event_ts = _ensure_utc(item.event_ts)
            has_ok = False
            user_logs = esmo_ok_map.get(emp.id, [])
            
            # Check if any log is within [event_ts - window, event_ts]
            # Since user_logs is sorted
            window_seconds = settings.ESMO_OK_WINDOW_HOURS * 3600
            for log_ts in reversed(user_logs): # Check newest first
                if log_ts > event_ts:
                    continue # Future event (shouldn't happen often if real-time)
                diff = (event_ts - log_ts).total_seconds()
                if diff <= window_seconds:
                    has_ok = True
                    break
                # If diff > window_seconds, and we are going backwards, older logs will also be > window
                if diff > window_seconds:
                    break
            
            if has_ok:
                status = "ACCEPTED"
            else:
                status = "REJECTED"
                reason = "No recent ESMO_OK"

        # Create Event Object
        status_enum = EventStatus(status)
        evt = Event(
            device_id=current_device_id,
            employee_id=emp.id,
            event_type=item.event_type,
            event_ts=_ensure_utc(item.event_ts),
            raw_id=item.raw_id,
            status=status_enum,
            reject_reason=reason,
            source_payload=item.payload,
        )
        final_events_to_insert.append(evt)

    # 7. Bulk Insert
    if final_events_to_insert:
        db.add_all(final_events_to_insert)
        try:
            db.commit()
            for evt in final_events_to_insert:
                # db.refresh(evt) # Not strictly needed if we trust the object state, but IDs are needed
                results.append(EventResult(
                    raw_id=evt.raw_id, 
                    status=evt.status.value, 
                    event_id=evt.id, 
                    reject_reason=evt.reject_reason
                ))
        except Exception as e:
            db.rollback()
            # If bulk fail, all fail
            # We could try fallback to single insert, but for now return error
            for evt in final_events_to_insert:
                 results.append(EventResult(raw_id=evt.raw_id, status="ERROR", reject_reason=str(e)))
                 
    # Sort results to match input order? 
    # The results list might be out of order relative to payload because we append "DUPLICATE" immediately
    # but "final_events_to_insert" are appended later.
    # To preserve order, we can map by raw_id or just return as is (client matches by raw_id)
    
    return results


@router.get("", response_model=list[EventOut])
def list_events(
    db: Session = Depends(get_db),
    _: Any = Depends(require_roles("superadmin", "admin", "dispatcher", "medical", "warehouse", "viewer")),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    employee_no: str | None = Query(default=None),
    device_id: int | None = Query(default=None),
    event_type: EventType | None = Query(default=None),
    status: EventStatus | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> list[EventOut]:
    query = db.query(Event)

    if date_from:
        query = query.filter(Event.event_ts >= _ensure_utc(date_from))
    if date_to:
        query = query.filter(Event.event_ts <= _ensure_utc(date_to))
    if device_id:
        query = query.filter(Event.device_id == device_id)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    if status:
        query = query.filter(Event.status == status)
    if employee_no:
        query = query.join(Employee).filter(Employee.employee_no.ilike(f"%{employee_no}%"))
    
    # Eager load employee for display
    query = query.options(joinedload(Event.employee))

    return query.order_by(Event.event_ts.desc()).limit(limit).all()
