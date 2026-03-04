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

from fastapi import APIRouter, Body, Depends, Query, Request, Response
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.hikvision_identity import (
    HIKVISION_MINE_SYSTEM,
    HIKVISION_SYSTEM,
    MINE_HOSTS,
    external_system_for_host,
    find_employee_by_external_id,
    normalize_external_id,
    upsert_employee_external_id,
)
from app.db.session import SessionLocal
from app.models.device import Device, DeviceType
from app.models.employee import Employee
from app.models.employee_external_id import EmployeeExternalID
from app.models.event import Event, EventStatus, EventType
from app.models.user import User

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


def _normalize_name(value: str | None) -> str:
    text = (value or "").strip().lower()
    if not text:
        return ""
    translate = str.maketrans({
        "ё": "е",
        "ў": "у",
        "ғ": "г",
        "қ": "к",
        "ҳ": "х",
        "’": "",
        "'": "",
        "`": "",
    })
    text = text.translate(translate)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _employee_short_name(employee: Employee) -> str:
    return _normalize_name(f"{employee.last_name} {employee.first_name}")


def _find_employee_by_name(db, payload_name: str) -> Employee | None:
    normalized = _normalize_name(payload_name)
    if not normalized:
        return None

    parts = normalized.split()
    if len(parts) < 2:
        return None

    last_part, first_part = parts[0], parts[1]
    candidates = (
        db.query(Employee)
        .filter(
            Employee.last_name.ilike(f"{last_part}%"),
            Employee.first_name.ilike(f"{first_part}%"),
        )
        .all()
    )
    exact = [c for c in candidates if _employee_short_name(c) == f"{last_part} {first_part}"]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _find_employee(db, employee_no: str, payload_name: str, ip_address: str) -> Employee | None:
    """Find employee by Hikvision employee number."""
    if not employee_no:
        return None

    normalized_payload_name = _normalize_name(payload_name)

    if ip_address in MINE_HOSTS:
        employee = find_employee_by_external_id(db, HIKVISION_MINE_SYSTEM, employee_no)
        if employee:
            return employee
        logger.warning(
            "[%s] Webhook mine mapping missing: employee_no=%s payload_name=%s system=%s",
            ip_address,
            employee_no,
            payload_name,
            HIKVISION_MINE_SYSTEM,
        )
        return None

    system = external_system_for_host(ip_address) or HIKVISION_SYSTEM
    employee = find_employee_by_external_id(db, system, employee_no)
    if employee and normalized_payload_name:
        if _employee_short_name(employee) not in normalized_payload_name:
            logger.debug(
                "[%s] Webhook external_id name mismatch: employee_no=%s payload_name=%s mapped=%s %s",
                ip_address,
                employee_no,
                payload_name,
                employee.last_name,
                employee.first_name,
            )
            return None
    if employee:
        return employee

    # Fallback: direct employee_no match
    employee = db.query(Employee).filter(Employee.employee_no == employee_no).first()
    if not employee:
        return None
    if normalized_payload_name and _employee_short_name(employee) not in normalized_payload_name:
        by_name = _find_employee_by_name(db, payload_name)
        if by_name:
            return by_name
        logger.debug(
            "[%s] Webhook employee_no name mismatch: employee_no=%s payload_name=%s mapped=%s %s",
            ip_address,
            employee_no,
            payload_name,
            employee.last_name,
            employee.first_name,
        )
        return None
    return employee


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
        "name": ace.get("name"),
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
        "name": ace_data.get("name", ""),
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

    request_ip = request.client.host if request.client else ""
    payload_ip = str(event_data.get("ipAddress", "")).strip()
    ip_address = payload_ip or request_ip
    if payload_ip and request_ip and payload_ip != request_ip:
        logger.warning(
            "Webhook source mismatch: request_ip=%s payload_ip=%s raw_id_hint=%s",
            request_ip,
            payload_ip,
            event_data.get("serialNo", ""),
        )
    if ip_address and ip_address not in DEVICE_IP_MAP:
        logger.warning("Ignoring webhook from unknown IP: %s (request_ip=%s)", ip_address, request_ip)
        return Response(status_code=200, content="OK")

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

        server_now = datetime.now(timezone(timedelta(hours=5)))
        event_ts = _select_event_ts(ip_address, event_data, server_now)
        
        # Determine event type
        event_type = _determine_direction(ip_address, event_data)

        payload_name = str(event_data.get("name", ""))
        normalized_payload_name = _normalize_name(payload_name)

        # Secondary dedup: same person can be emitted twice with different IDs/serials.
        if normalized_payload_name:
            nearby = (
                db.query(Event)
                .filter(
                    Event.device_id == device.id,
                    Event.event_type == event_type,
                    Event.event_ts >= event_ts - timedelta(seconds=DEDUP_SECONDS),
                    Event.event_ts <= event_ts + timedelta(seconds=DEDUP_SECONDS),
                )
                .all()
            )
            if any(
                _normalize_name((evt.source_payload or {}).get("name", "")) == normalized_payload_name
                for evt in nearby
            ):
                return Response(status_code=200, content="OK")

        # Find employee
        employee = _find_employee(db, employee_no, payload_name, ip_address)
        if not employee:
            logger.warning("Employee not found for ID: %s", employee_no)
            print(f"DEBUG: Employee not found for ID: {employee_no}")
            # Still save the event with a log, but skip if no employee
            return Response(status_code=200, content="OK")

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
            source_payload={
                **event_data,
                "source_host": ip_address,
                "source_request_ip": request_ip,
            },
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


@router.post("/sync-mine-id-mappings")
def sync_mine_id_mappings(
    current_user: Any = Depends(get_current_user),
) -> dict:
    """
    Build/refresh strict EmployeeExternalID mappings for mine turnstiles.
    - source IDs come from mine devices (employeeNo field)
    - target system is EmployeeExternalID.system == 'HIKVISION_MINE'
    - runtime mine ingestion then relies only on this mapping (no name fallback)
    """
    if current_user.role not in ("superadmin", "admin", "dispatcher"):
        return Response(status_code=403, content="Not authorized")

    try:
        devices = json.loads(settings.HIKVISION_DEVICES)
    except Exception:
        return {"success": False, "message": "Invalid device config"}

    mine_devices = [d for d in (devices or []) if str(d.get("host", "")).strip() in MINE_HOSTS]
    if not mine_devices:
        return {"success": False, "message": "No mine devices configured"}

    from app.core.hikvision_client import HikvisionClient

    db = SessionLocal()
    scanned_users = 0
    created = 0
    updated = 0
    unchanged = 0
    unresolved = 0
    conflicts = 0
    unreachable: list[str] = []
    unresolved_samples: list[dict[str, str]] = []

    try:
        for device_conf in mine_devices:
            host = str(device_conf.get("host", "")).strip()
            client = HikvisionClient(
                host=host,
                user=settings.HIKVISION_USER,
                password=settings.HIKVISION_PASS,
            )
            if not client.check_connection():
                unreachable.append(host)
                continue

            users = client.fetch_all_users()
            for user_data in users:
                scanned_users += 1
                raw_external = str(user_data.get("employeeNo", "")).strip()
                external_id = normalize_external_id(raw_external)
                full_name = str(user_data.get("name", "")).strip()
                if not external_id:
                    continue

                employee = _find_employee_by_name(db, full_name)
                if not employee:
                    unresolved += 1
                    if len(unresolved_samples) < 100:
                        unresolved_samples.append(
                            {
                                "host": host,
                                "external_id": external_id,
                                "name": full_name,
                            }
                        )
                    continue

                status = upsert_employee_external_id(
                    db,
                    employee_id=int(employee.id),
                    system=HIKVISION_MINE_SYSTEM,
                    external_id=external_id,
                )
                if status == "created":
                    created += 1
                elif status == "updated":
                    updated += 1
                elif status == "unchanged":
                    unchanged += 1
                elif status == "conflict_external_taken":
                    conflicts += 1

        db.commit()

        return {
            "success": True,
            "system": HIKVISION_MINE_SYSTEM,
            "devices": [str(d.get("host", "")).strip() for d in mine_devices],
            "unreachable": unreachable,
            "scanned_users": scanned_users,
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "conflicts": conflicts,
            "unresolved": unresolved,
            "unresolved_samples": unresolved_samples,
        }
    except Exception as exc:
        db.rollback()
        logger.error("Mine mapping sync failed: %s", exc)
        return {"success": False, "message": str(exc)}
    finally:
        db.close()


@router.get("/source-audit")
def hikvision_source_audit(
    target_date: str | None = Query(default=None),
    _: Any = Depends(get_current_user),
) -> dict:
    """
    Verify that events are sourced from their own turnstile devices and
    direction/host mapping remains consistent.
    """
    local_tz = timezone(timedelta(hours=5))
    if target_date:
        try:
            day = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            return {"success": False, "message": "target_date must be YYYY-MM-DD"}
    else:
        day = datetime.now(local_tz).date()

    start_local = datetime(day.year, day.month, day.day, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    db = SessionLocal()
    try:
        rows = (
            db.query(Event, Device)
            .join(Device, Device.id == Event.device_id)
            .filter(
                Event.event_ts >= start_utc,
                Event.event_ts < end_utc,
                Event.event_type.in_([EventType.TURNSTILE_IN, EventType.TURNSTILE_OUT]),
            )
            .all()
        )

        by_host_type: dict[str, dict[str, int]] = {}
        unknown_hosts = 0
        wrong_direction = 0
        payload_host_mismatch = 0
        wrong_direction_samples: list[dict[str, str]] = []
        payload_mismatch_samples: list[dict[str, str]] = []
        mine_payload_ids: set[str] = set()

        for event_obj, device_obj in rows:
            host = str(device_obj.host or "")
            event_type = str(event_obj.event_type.value if hasattr(event_obj.event_type, "value") else event_obj.event_type)
            bucket = by_host_type.setdefault(host, {})
            bucket[event_type] = bucket.get(event_type, 0) + 1

            if host not in DEVICE_IP_MAP:
                unknown_hosts += 1
            else:
                expected = DEVICE_IP_MAP[host]["direction"]
                if event_obj.event_type != expected:
                    wrong_direction += 1
                    if len(wrong_direction_samples) < 30:
                        wrong_direction_samples.append(
                            {
                                "event_id": str(event_obj.id),
                                "host": host,
                                "device_name": str(device_obj.name or ""),
                                "event_type": event_type,
                                "expected": str(expected.value if hasattr(expected, "value") else expected),
                                "raw_id": str(event_obj.raw_id or ""),
                            }
                        )

            payload = event_obj.source_payload or {}
            payload_host = str(
                payload.get("source_host")
                or payload.get("ipAddress")
                or payload.get("deviceIP")
                or payload.get("devIp")
                or ""
            ).strip()
            if payload_host and host and payload_host != host:
                payload_host_mismatch += 1
                if len(payload_mismatch_samples) < 30:
                    payload_mismatch_samples.append(
                        {
                            "event_id": str(event_obj.id),
                            "host": host,
                            "payload_host": payload_host,
                            "raw_id": str(event_obj.raw_id or ""),
                        }
                    )

            if host in MINE_HOSTS:
                payload_no = str(payload.get("employeeNoString") or payload.get("cardNo") or "").strip()
                payload_no = normalize_external_id(payload_no)
                if payload_no:
                    mine_payload_ids.add(payload_no)

        mapped_ids = {
            str(row.external_id)
            for row in db.query(EmployeeExternalID)
            .filter(EmployeeExternalID.system == HIKVISION_MINE_SYSTEM)
            .all()
        }
        mine_missing_mapping_ids = sorted(mine_payload_ids - mapped_ids)

        return {
            "success": True,
            "date": day.isoformat(),
            "total_events": len(rows),
            "by_host_type": by_host_type,
            "unknown_hosts": unknown_hosts,
            "wrong_direction": wrong_direction,
            "wrong_direction_samples": wrong_direction_samples,
            "payload_host_mismatch": payload_host_mismatch,
            "payload_host_mismatch_samples": payload_mismatch_samples,
            "mine_payload_ids_seen": len(mine_payload_ids),
            "mine_external_ids_mapped": len(mapped_ids),
            "mine_missing_mapping_ids": mine_missing_mapping_ids[:200],
            "mine_missing_mapping_count": len(mine_missing_mapping_ids),
            "expected_direction_map": {
                host: str(meta["direction"].value if hasattr(meta["direction"], "value") else meta["direction"])
                for host, meta in DEVICE_IP_MAP.items()
            },
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
