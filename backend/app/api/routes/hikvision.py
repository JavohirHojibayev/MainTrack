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
import re

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

# Mapping based on user request and iVMS
DEVICE_IP_MAP = {
    "192.168.0.223": {"name": "Kirish-1", "direction": EventType.TURNSTILE_IN},
    "192.168.0.221": {"name": "Kirish-2", "direction": EventType.TURNSTILE_IN},
    "192.168.0.219": {"name": "Kirish-3", "direction": EventType.TURNSTILE_IN},
    "192.168.1.181": {"name": "shaxta kirish", "direction": EventType.TURNSTILE_IN},
    "192.168.1.180": {"name": "shaxta chiqish", "direction": EventType.TURNSTILE_OUT},
    "192.168.0.224": {"name": "Chiqish-1", "direction": EventType.TURNSTILE_OUT},
    "192.168.0.222": {"name": "Chiqish-2", "direction": EventType.TURNSTILE_OUT},
    "192.168.0.220": {"name": "Chiqish-3", "direction": EventType.TURNSTILE_OUT},
}

DEDUP_SECONDS = max(settings.TURNSTILE_DEDUP_SECONDS, 1)


# ─── Webhook Receiver (no auth — called by turnstile devices) ─────────

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
            
        # Enforce name from map if available
        if ip in DEVICE_IP_MAP:
            mapped_name = DEVICE_IP_MAP[ip]["name"]
            if device.name != mapped_name:
                device.name = mapped_name
                
        db.commit()
        return device

    initial_name = f"Turnstile-{ip}"
    if ip in DEVICE_IP_MAP:
        initial_name = DEVICE_IP_MAP[ip]["name"]

    device = Device(
        name=initial_name,
        device_code=device_code,
        host=ip,
        device_type=DeviceType.HIKVISION,
        location=initial_name,
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


def _flatten_hikvision_json(data: dict) -> dict:
    """Flatten nested Hikvision JSON structure to match XML output."""
    ace = data.get("AccessControllerEvent", {})
    return {
        "ipAddress": data.get("ipAddress"),
        "macAddress": data.get("macAddress"),
        "dateTime": data.get("dateTime"),
        "eventType": data.get("eventType"),
        "eventState": data.get("eventState"),
        "eventDescription": data.get("eventDescription"),
        # Flattened fields from AccessControllerEvent
        "employeeNoString": ace.get("employeeNoString", ace.get("employeeNo")),
        "cardNo": ace.get("cardNo"),
        "cardReaderNo": str(ace.get("cardReaderNo", "")),
        "doorNo": str(ace.get("doorNo", "")),
        "serialNo": str(ace.get("serialNo", "")),
        "currentVerifyMode": ace.get("currentVerifyMode"),
    }


def _parse_event_xml(xml_body: str) -> dict | None:
    """Parse Hikvision EventNotificationAlert XML into a dict."""
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError as exc:
        logger.warning("XML parse error: %s. Body: %r", exc, xml_body)
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


def _determine_direction(ip_address: str, event_data: dict) -> EventType:
    """Determine TURNSTILE_IN or TURNSTILE_OUT from event data or IP mapping."""
    
    # 1. Check IP mapping first (strongest signal)
    if ip_address in DEVICE_IP_MAP:
        return DEVICE_IP_MAP[ip_address]["direction"]

    # 2. Fallback to existing logic
    # Check cardReaderNo or doorNo
    # Convention: reader 1 / odd door = IN, reader 2 / even door = OUT
    reader_no = int(event_data.get("cardReaderNo", "0") or "0")
    door_no = int(event_data.get("doorNo", "1") or "1")
    event_desc = str(event_data.get("eventDescription", "")).lower()

    if "exit" in event_desc or "out" in event_desc:
        return EventType.TURNSTILE_OUT
    if "entry" in event_desc or "in" in event_desc:
        return EventType.TURNSTILE_IN

    # Reader 2 or even door = OUT
    if reader_no == 2 or (door_no % 2 == 0):
        return EventType.TURNSTILE_OUT

    return EventType.TURNSTILE_IN


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


def _select_event_ts(ip_address: str, event_data: dict, server_now: datetime) -> datetime:
    """Use payload timestamp when available, fallback to server time.

    This prevents replayed historical buffers from appearing as "current"
    passes when devices resend old events.
    """
    raw = str(event_data.get("dateTime") or event_data.get("time") or "").strip()
    if raw:
        return _parse_hikvision_time(raw)
    return server_now


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
    print(f"DEBUG: Webhook received from {request.client.host if request.client else 'unknown'}")

    # Try to parse as JSON first (or JSON inside multipart)
    json_data = None
    
    # 1. Try direct JSON
    try:
        json_data = json.loads(xml_str)
    except json.JSONDecodeError:
        pass

    # 2. Try simple regex (non-greedy)
    if not json_data:
        # Look for a clean JSON block containing "AccessControllerEvent"
        match = re.search(r'(\{.*?"AccessControllerEvent":.*?\})', xml_str, re.DOTALL)
        if match:
            try:
                json_data = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # 3. Try splitting by boundary (heuristic)
    if not json_data and "--" in xml_str:
        # Hikvision often uses "--MIME_boundary" or similar
        # We split by any line starting with --
        parts = re.split(r'\r?\n--', xml_str)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Find first { and last }
            start = part.find("{")
            end = part.rfind("}")
            if start != -1 and end != -1:
                candidate = part[start:end+1]
                try:
                    json_data = json.loads(candidate)
                    if "AccessControllerEvent" in json_data or "eventType" in json_data:
                        break
                    else:
                        json_data = None # Not the event payload
                except json.JSONDecodeError:
                    continue

    if json_data:
        event_data = _flatten_hikvision_json(json_data)
    else:
        # 4. Fallback to XML
        event_data = _parse_event_xml(xml_str)
        
    print(f"DEBUG: Parsed event_data: {event_data}")

    if not event_data:
        # Log limited preview of body to avoid binary dump
        preview = xml_str[:1000].replace('\r', '').replace('\n', ' ') + "..." if len(xml_str) > 1000 else xml_str
        logger.warning("Could not parse webhook payload. Body preview: %s", preview)
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
        if not device.is_active:
            logger.info("Ignored webhook event from disabled device: %s", device.device_code)
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
            logger.warning("Employee not found for ID: %s", employee_no)
            print(f"DEBUG: Employee not found for ID: {employee_no}")
            # Still save the event with a log, but skip if no employee
            return Response(status_code=200, content="OK")

        server_now = datetime.now(timezone(timedelta(hours=5)))
        event_ts = _select_event_ts(ip_address, event_data, server_now)
        
        # Determine event type
        event_type = _determine_direction(ip_address, event_data)

        # Debounce: ignore repeated reads from the same device in a short window.
        recent_event = (
            db.query(Event)
            .filter(
                Event.device_id == device.id,
                Event.employee_id == employee.id,
                Event.event_type == event_type,
                Event.event_ts >= event_ts - timedelta(seconds=DEDUP_SECONDS),
                Event.event_ts <= event_ts + timedelta(seconds=1),
            )
            .first()
        )

        if recent_event:
            logger.info("Debounced duplicate event for employee %s (type=%s)", employee_no, event_type)
            print(f"DEBUG: Debounced duplicate event for {employee_no}")
            return Response(status_code=200, content="OK")

        event = Event(
            device_id=device.id,
            employee_id=employee.id,
            event_type=event_type,
            event_ts=event_ts,
            raw_id=raw_id,
            status=EventStatus.ACCEPTED,
            source_payload=event_data,
        )
        db.add(event)
        db.commit()
        logger.info(
            "Saved event: employee=%s, type=%s, device=%s, ts=%s",
            employee_no,
            event.event_type.value,
            ip_address,
            event_ts,
        )
        print(f"DEBUG: Saved event for {employee_no} at {event_ts}")
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
                "last_seen": db_device.last_seen.isoformat() if db_device and db_device.last_seen else None,
            })

        return {
            "configured": True,
            "mode": "webhook (HTTP Listening)",
            "total": len(devices),
            "devices": device_statuses,
        }
    finally:
        db.close()


@router.post("/sync-users")
def start_user_sync(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Manually trigger synchronization of users from Hikvision turnstiles.
    Fetches all users from the first configured device and adds missing ones to DB.
    """
    # Only admins/dispatchers/etc can sync
    if current_user.role not in ("superadmin", "admin", "dispatcher"):
        return Response(status_code=403, content="Not authorized")

    try:
        devices = json.loads(settings.HIKVISION_DEVICES)
    except:
        return {"success": False, "message": "Invalid device config"}

    if not devices:
        return {"success": False, "message": "No devices configured"}

    # Use first device for sync
    device_conf = devices[0]
    host = device_conf.get("host")
    
    from app.core.hikvision_client import HikvisionClient
    
    client = HikvisionClient(
        host=host,
        user=settings.HIKVISION_USER,
        password=settings.HIKVISION_PASS
    )

    if not client.check_connection():
         return {"success": False, "message": f"Could not connect to turnstile {host}"}

    users = client.fetch_all_users()
    logger.info("Sync found %d users on device", len(users))

    db = SessionLocal()
    added_count = 0
    skipped_count = 0
    
    try:
        for u in users:
            emp_no = u.get("employeeNo")
            name = u.get("name", "")
            
            if not emp_no:
                continue

            # Check if exists
            existing = db.query(Employee).filter(Employee.employee_no == emp_no).first()
            if existing:
                skipped_count += 1
                continue

            # Create new employee
            # Parse name: "Last First Middle"
            parts = name.split()
            last_name = parts[0] if len(parts) > 0 else "Unknown"
            first_name = parts[1] if len(parts) > 1 else ""
            patronymic = " ".join(parts[2:]) if len(parts) > 2 else ""

            new_emp = Employee(
                employee_no=emp_no,
                first_name=first_name,
                last_name=last_name,
                patronymic=patronymic,
                position="Synced from Turnstile",
                department="General",
                is_active=True
            )
            db.add(new_emp)
            added_count += 1

        db.commit()
        return {
            "success": True,
            "message": f"Sync complete. Added {added_count} new employees.",
            "total_on_device": len(users),
            "added": added_count,
            "skipped": skipped_count
        }
    except Exception as e:
        logger.error("Sync failed: %s", e)
        return {"success": False, "message": str(e)}
    finally:
        db.close()

@router.post("/fix-names")
def fix_device_names_endpoint() -> dict:
    """Force update device names from DEVICE_IP_MAP."""
    db = SessionLocal()
    try:
        updated = 0
        details = []
        for ip, config in DEVICE_IP_MAP.items():
            mapped_name = config["name"]
            device = db.query(Device).filter(Device.host == ip).first()
            if device:
                if device.name != mapped_name:
                    old_name = device.name
                    device.name = mapped_name
                    device.location = mapped_name
                    details.append(f"{ip}: UPDATED {old_name} -> {mapped_name}")
                    updated += 1
                else:
                    details.append(f"{ip}: OK (Already {device.name})")
            else:
                 details.append(f"{ip}: NOT FOUND in DB")
        

        if updated > 0:
            db.commit()

        # List all devices for verification
        all_devices = db.query(Device).all()
        for d in all_devices:
            details.append(f"DB RECORD: id={d.id} name='{d.name}' host='{d.host}' code='{d.device_code}'")
            
        return {"success": True, "updated_count": updated, "details": details}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()
