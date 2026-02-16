"""
Hikvision API routes — webhook receiver, status check, and manual sync.

The webhook endpoint receives real-time event pushes from Hikvision turnstiles
via their HTTP Listening feature. This is a PUSH model — the turnstile sends
events TO MineTrack, so MineTrack doesn't need to connect TO the turnstile.

Safety: MineTrack never writes to or modifies turnstile devices.
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, Request, Response
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import SessionLocal
from app.models.device import Device, DeviceType
from app.models.employee import Employee
from app.models.employee_external_id import EmployeeExternalID
from app.models.event import Event, EventStatus, EventType

logger = logging.getLogger("hikvision.webhook")

router = APIRouter()


# ─── Webhook Receiver (no auth — called by turnstile devices) ─────────

# ... (helper functions remain the same) ...
# I will NOT include helper functions in ReplacementContent to rely on existing context,
# but replace_file_content requires exact context matching.
# I will target the imports and the route definition separately or use multi_replace.


def _get_or_create_device_by_ip(db, ip: str, mac: str = "") -> Device | None:
    """Find or create a device record by IP address."""
    device_code = f"HIK_{ip.replace('.', '_')}"
    device = db.query(Device).filter(Device.device_code == device_code).first()
    
    now = datetime.now(timezone.utc)
    
    if device:
        # Update last_seen and host if missing
        device.last_seen = now
        if not device.host:
            device.host = ip
        db.commit()
        return device

    device = Device(
        name=f"Turnstile-{ip}",
        device_code=device_code,
        host=ip,
        device_type=DeviceType.HIKVISION,
        location=f"Turnstile-{ip}",
        api_key=f"hikvision_{device_code}",
        is_active=True,
        last_seen=now,
    )
    db.add(device)
    try:
        db.commit()
        db.refresh(device)
        logger.info("Created device with host: %s", ip)
    except IntegrityError:
        db.rollback()
        device = db.query(Device).filter(Device.device_code == device_code).first()
        if device:
            device.last_seen = now
            db.commit()
            
    return device


def _find_employee(db, employee_no: str) -> Employee | None:
    """Find employee by Hikvision employee number."""
    if not employee_no:
        return None

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


def _parse_event_xml(xml_body: str) -> dict | None:
    """Parse Hikvision EventNotificationAlert XML into a dict."""
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError as exc:
        logger.warning("XML parse error: %s", exc)
        return None

    # Remove namespace prefixes for easier access
    ns = ""
    for key in ("http://www.hikvision.com/ver20/XMLSchema",
                "http://www.std-cgi.com/ver20/XMLSchema"):
        if root.tag.startswith(f"{{{key}}}"):
            ns = f"{{{key}}}"
            break

    def _text(tag: str) -> str:
        el = root.find(f"{ns}{tag}")
        if el is not None and el.text:
            return el.text.strip()
        return ""

    # Get nested AccessControllerEvent data
    ace = root.find(f"{ns}AccessControllerEvent")
    if ace is None:
        # Try without namespace
        ace = root.find("AccessControllerEvent")

    ace_data = {}
    if ace is not None:
        for child in ace:
            tag = child.tag.replace(ns, "").split("}")[-1]
            ace_data[tag] = child.text.strip() if child.text else ""

    return {
        "ipAddress": _text("ipAddress"),
        "macAddress": _text("macAddress"),
        "dateTime": _text("dateTime"),
        "eventType": _text("eventType"),
        "eventState": _text("eventState"),
        "eventDescription": _text("eventDescription"),
        **ace_data,
    }


def _determine_direction(event_data: dict) -> EventType:
    """Determine TURNSTILE_IN or TURNSTILE_OUT from event data."""
    # Check cardReaderNo or doorNo
    # Convention: reader 1 / odd door = IN, reader 2 / even door = OUT
    reader_no = int(event_data.get("cardReaderNo", "0") or "0")
    door_no = int(event_data.get("doorNo", "1") or "1")
    event_desc = str(event_data.get("eventDescription", "")).lower()

    if "exit" in event_desc or "out" in event_desc:
        return EventType.MINE_OUT
    if "entry" in event_desc or "in" in event_desc:
        return EventType.MINE_IN

    # Reader 2 or even door = OUT
    if reader_no == 2 or (door_no % 2 == 0):
        return EventType.MINE_OUT

    return EventType.MINE_IN


def _parse_hikvision_time(time_str: str) -> datetime:
    """Parse Hikvision time format."""
    if not time_str:
        return datetime.now(timezone(timedelta(hours=5)))
    try:
        if "+" in time_str or time_str.endswith("Z"):
            return datetime.fromisoformat(time_str)
        return datetime.fromisoformat(time_str).replace(
            tzinfo=timezone(timedelta(hours=5))
        )
    except (ValueError, TypeError):
        return datetime.now(timezone(timedelta(hours=5)))


@router.post("/webhook", include_in_schema=False)
def hikvision_webhook(request: Request, body: bytes = Body(...)) -> Response:
    """
    Receive real-time event notifications from Hikvision turnstiles.

    This endpoint is called BY the turnstile device (HTTP Listening feature).
    No authentication required — the turnstile cannot send auth headers.
    The endpoint only RECEIVES data — it never sends commands back.
    """
    # body is already read as bytes by FastAPI because of Body(...)
    xml_str = body.decode("utf-8", errors="replace")

    logger.info("Webhook received (%d bytes) from %s", len(body), request.client.host if request.client else "unknown")

    # Parse the XML notification
    event_data = _parse_event_xml(xml_str)
    if not event_data:
        logger.warning("Could not parse webhook XML")
        return Response(status_code=200, content="OK")

    # Only process AccessControllerEvent
    if event_data.get("eventType") not in ("AccessControllerEvent", ""):
        logger.debug("Ignoring non-access event: %s", event_data.get("eventType"))
        return Response(status_code=200, content="OK")

    ip_address = event_data.get("ipAddress", request.client.host if request.client else "")
    employee_no = event_data.get("employeeNoString", event_data.get("cardNo", ""))
    serial_no = event_data.get("serialNo", "")
    event_time = event_data.get("dateTime", "")

    # Build raw_id for deduplication
    raw_id = serial_no or f"{event_time}_{employee_no}"
    if not raw_id:
        return Response(status_code=200, content="OK")

    db = SessionLocal()
    try:
        # Find/create device
        device = _get_or_create_device_by_ip(db, ip_address, event_data.get("macAddress", ""))
        if not device:
            return Response(status_code=200, content="OK")

        # Check duplicate
        existing = (
            db.query(Event)
            .filter(Event.device_id == device.id, Event.raw_id == raw_id)
            .first()
        )
        if existing:
            return Response(status_code=200, content="OK")

        # Find employee
        employee = _find_employee(db, employee_no)
        if not employee:
            logger.debug("Employee not found for ID: %s", employee_no)
            # Still save the event with a log, but skip if no employee
            return Response(status_code=200, content="OK")

        # Create event
        event = Event(
            device_id=device.id,
            employee_id=employee.id,
            event_type=_determine_direction(event_data),
            event_ts=_parse_hikvision_time(event_time),
            raw_id=raw_id,
            status=EventStatus.ACCEPTED,
            source_payload=event_data,
        )
        db.add(event)
        db.commit()
        logger.info(
            "Saved event: employee=%s, type=%s, device=%s",
            employee_no,
            event.event_type.value,
            ip_address,
        )
    except IntegrityError:
        db.rollback()
    except Exception as exc:
        logger.error("Webhook processing error: %s", exc)
        db.rollback()
    finally:
        db.close()

    return Response(status_code=200, content="OK")


# ─── Authenticated API endpoints (for MineTrack UI) ──────────────────

@router.get("/status")
def hikvision_status(_: Any = Depends(get_current_user)) -> dict:
    """Check configured Hikvision devices."""
    try:
        devices = json.loads(settings.HIKVISION_DEVICES)
    except (json.JSONDecodeError, TypeError):
        devices = []

    if not devices:
        return {"configured": False, "devices": [], "message": "No Hikvision devices configured"}

    db = SessionLocal()
    try:
        device_statuses = []
        for dev in devices:
            host = dev.get("host", "")
            name = dev.get("name", host)
            device_code = f"HIK_{host.replace('.', '_')}"

            db_device = db.query(Device).filter(Device.device_code == device_code).first()
            event_count = 0
            last_event = None
            if db_device:
                event_count = db.query(Event).filter(Event.device_id == db_device.id).count()
                latest = (
                    db.query(Event)
                    .filter(Event.device_id == db_device.id)
                    .order_by(Event.event_ts.desc())
                    .first()
                )
                if latest:
                    last_event = latest.event_ts.isoformat()

            device_statuses.append({
                "name": name,
                "host": host,
                "registered": db_device is not None,
                "event_count": event_count,
                "last_event": last_event,
            })

        return {
            "configured": True,
            "mode": "webhook (HTTP Listening)",
            "total": len(devices),
            "devices": device_statuses,
        }
    finally:
        db.close()
