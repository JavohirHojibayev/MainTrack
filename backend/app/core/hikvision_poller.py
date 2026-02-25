"""
Hikvision Background Poller — periodically reads events from turnstile devices.

This service runs in the background and:
1. Connects to each Hikvision device via ISAPI (READ-ONLY)
2. Fetches new access control events
3. Saves them to MineTrack's own PostgreSQL database
4. NEVER writes to or modifies the turnstile devices

Safety guarantees:
- Only GET/POST-search (read-only) requests to turnstile
- Errors are caught and logged, never crash the main application
- Duplicate events are prevented via raw_id UniqueConstraint
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.hikvision_client import HikvisionClient
from app.db.session import SessionLocal
from app.models.device import Device, DeviceType
from app.models.employee import Employee
from app.models.employee_external_id import EmployeeExternalID
from app.models.event import Event, EventStatus, EventType

logger = logging.getLogger("hikvision.poller")

DEVICE_IP_MAP = {
    "192.168.0.223": EventType.TURNSTILE_IN,
    "192.168.0.221": EventType.TURNSTILE_IN,
    "192.168.0.219": EventType.TURNSTILE_IN,
    "192.168.0.224": EventType.TURNSTILE_OUT,
    "192.168.0.222": EventType.TURNSTILE_OUT,
    "192.168.0.220": EventType.TURNSTILE_OUT,
}

DEDUP_SECONDS = max(settings.TURNSTILE_DEDUP_SECONDS, 1)


def _parse_devices() -> list[dict]:
    """Parse HIKVISION_DEVICES from settings (JSON string)."""
    try:
        devices = json.loads(settings.HIKVISION_DEVICES)
        if isinstance(devices, list):
            return devices
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _get_or_create_device(db: Session, device_info: dict) -> Device | None:
    """Find or create a device record in MineTrack DB (not on the turnstile!)."""
    host = device_info.get("host", "")
    name = device_info.get("name", host)
    device_code = f"HIK_{host.replace('.', '_')}"
    now = datetime.now(timezone.utc)

    device = db.query(Device).filter(Device.device_code == device_code).first()
    if device:
        device.last_seen = now
        if host and not device.host:
            device.host = host
        return device

    # Create new device in MineTrack DB
    device = Device(
        name=name,
        device_code=device_code,
        device_type=DeviceType.HIKVISION,
        location=name,
        api_key=f"hikvision_{device_code}",
        is_active=True,
        host=host or None,
        last_seen=now,
    )
    db.add(device)
    try:
        db.commit()
        db.refresh(device)
        logger.info("Created device record: %s (%s)", name, device_code)
    except IntegrityError:
        db.rollback()
        device = db.query(Device).filter(Device.device_code == device_code).first()
    return device


def _find_employee_by_hikvision_id(db: Session, employee_no: str) -> Employee | None:
    """Find employee by Hikvision card/employee number.

    First tries EmployeeExternalID (system='HIKVISION'),
    then falls back to employee_no match.
    """
    # Try external ID lookup
    ext = (
        db.query(EmployeeExternalID)
        .filter(
            EmployeeExternalID.system == "HIKVISION",
            EmployeeExternalID.external_id == employee_no,
        )
        .first()
    )
    if ext:
        return db.query(Employee).filter(Employee.id == ext.employee_id).first()

    # Fallback: direct employee_no match
    return db.query(Employee).filter(Employee.employee_no == employee_no).first()


def _determine_event_type(event_data: dict, host: str, device_name: str) -> EventType:
    """Determine TURNSTILE_IN or TURNSTILE_OUT from Hikvision event data."""
    if host in DEVICE_IP_MAP:
        return DEVICE_IP_MAP[host]

    name_l = (device_name or "").lower()
    if "kirish" in name_l or "entry" in name_l:
        return EventType.TURNSTILE_IN
    if "chiqish" in name_l or "exit" in name_l:
        return EventType.TURNSTILE_OUT

    # Hikvision major=5 (Access Control), minor types:
    # 75 = Face Authentication Passed (IN)
    # 76 = Face Auth Failed
    # Common approach: check door direction or event description
    minor = event_data.get("minor", 0)
    event_type_str = str(event_data.get("eventType", "")).lower()

    # If event has direction info
    if "in" in event_type_str or "entry" in event_type_str:
        return EventType.TURNSTILE_IN
    if "out" in event_type_str or "exit" in event_type_str:
        return EventType.TURNSTILE_OUT

    # Default: check currentVerifyMode or use IN as default
    # Door number even = OUT, odd = IN (common convention)
    door_no = event_data.get("doorNo", 1)
    if door_no % 2 == 0:
        return EventType.TURNSTILE_OUT

    return EventType.TURNSTILE_IN


def _parse_hikvision_time(time_str: str) -> datetime:
    """Parse Hikvision time format to timezone-aware datetime."""
    # Format: "2026-02-13T08:30:00+05:00" or "2026-02-13T08:30:00"
    try:
        if "+" in time_str or time_str.endswith("Z"):
            return datetime.fromisoformat(time_str)
        return datetime.fromisoformat(time_str).replace(tzinfo=timezone(timedelta(hours=5)))
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def poll_single_device(device_info: dict) -> int:
    """Poll a single Hikvision device for new events. Returns count of new events saved."""
    host = device_info.get("host", "")
    port = device_info.get("port", 80)
    name = device_info.get("name", host)

    if not host:
        return 0

    client = HikvisionClient(
        host=host,
        port=port,
        user=settings.HIKVISION_USER,
        password=settings.HIKVISION_PASS,
    )

    # Time window: last 5 minutes (overlap to catch any missed events)
    now = datetime.now(timezone(timedelta(hours=5)))
    start_time = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S+05:00")
    end_time = now.strftime("%Y-%m-%dT%H:%M:%S+05:00")

    events = client.fetch_access_events(start_time, end_time)
    if not events:
        return 0

    db: Session = SessionLocal()
    saved_count = 0
    try:
        device = _get_or_create_device(db, device_info)
        if not device:
            logger.error("Could not find/create device for %s", name)
            return 0

        for evt_data in events:
            event_time_raw = str(evt_data.get("time", ""))

            # Check duplicate (by device_id + raw_id)
            # Find employee
            employee_no = str(evt_data.get("employeeNoString", evt_data.get("cardNo", "")))
            if not employee_no:
                continue

            raw_id = str(evt_data.get("serialNo", "")).strip()
            if not raw_id:
                raw_id = f"{employee_no}:{event_time_raw}:{host}"
            if not raw_id:
                continue

            existing = (
                db.query(Event)
                .filter(Event.device_id == device.id, Event.raw_id == raw_id)
                .first()
            )
            if existing:
                continue

            employee = _find_employee_by_hikvision_id(db, employee_no)
            if not employee:
                logger.debug("Employee not found for Hikvision ID: %s", employee_no)
                continue

            event_ts = _parse_hikvision_time(event_time_raw)
            event_type = _determine_event_type(evt_data, host, device.name if device else name)

            # Debounce repeated reads from the same passage.
            dup = (
                db.query(Event)
                .filter(
                    Event.device_id == device.id,
                    Event.employee_id == employee.id,
                    Event.event_type == event_type,
                    Event.status == EventStatus.ACCEPTED,
                    Event.event_ts >= event_ts - timedelta(seconds=DEDUP_SECONDS),
                    Event.event_ts <= event_ts + timedelta(seconds=DEDUP_SECONDS),
                )
                .first()
            )
            if dup:
                continue

            # Create event in MineTrack DB
            event = Event(
                device_id=device.id,
                employee_id=employee.id,
                event_type=event_type,
                event_ts=event_ts,
                raw_id=raw_id,
                status=EventStatus.ACCEPTED,
                source_payload=evt_data,
            )
            db.add(event)

            try:
                db.commit()
                saved_count += 1
            except IntegrityError:
                db.rollback()  # Duplicate — skip silently

        logger.info("[%s] Saved %d new events", name, saved_count)
    except Exception as exc:
        logger.error("[%s] Polling error: %s", name, exc)
        db.rollback()
    finally:
        db.close()

    return saved_count


def poll_all_devices() -> dict[str, int]:
    """Poll all configured Hikvision devices. Returns {device_name: saved_count}."""
    devices = _parse_devices()
    if not devices:
        logger.debug("No Hikvision devices configured")
        return {}

    results: dict[str, int] = {}
    for dev in devices:
        name = dev.get("name", dev.get("host", "unknown"))
        try:
            count = poll_single_device(dev)
            results[name] = count
        except Exception as exc:
            logger.error("[%s] Unexpected error: %s", name, exc)
            results[name] = -1

    return results


async def hikvision_polling_loop():
    """Background async loop that polls devices every N seconds."""
    interval = max(settings.HIKVISION_POLL_INTERVAL, 10)  # Minimum 10 seconds
    devices = _parse_devices()

    if not devices:
        logger.info("Hikvision polling disabled — no devices configured")
        return

    logger.info(
        "Hikvision polling started: %d devices, every %ds",
        len(devices),
        interval,
    )

    while True:
        try:
            # Run blocking I/O in thread pool (does not block event loop)
            await asyncio.get_event_loop().run_in_executor(None, poll_all_devices)
        except Exception as exc:
            logger.error("Hikvision polling cycle error: %s", exc)

        await asyncio.sleep(interval)
