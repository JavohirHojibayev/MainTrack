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
import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.hikvision_client import HikvisionClient
from app.core.hikvision_identity import (
    HIKVISION_MINE_SYSTEM,
    HIKVISION_SYSTEM,
    MINE_HOSTS,
    external_system_for_host,
    find_employee_by_external_id,
)
from app.db.session import SessionLocal
from app.models.device import Device, DeviceType
from app.models.employee import Employee
from app.models.event import Event, EventStatus, EventType

logger = logging.getLogger("hikvision.poller")

DEVICE_IP_MAP = {
    "192.168.0.223": EventType.TURNSTILE_IN,
    "192.168.0.221": EventType.TURNSTILE_IN,
    "192.168.0.219": EventType.TURNSTILE_IN,
    "192.168.1.181": EventType.TURNSTILE_IN,
    "192.168.1.180": EventType.TURNSTILE_OUT,
    "192.168.0.224": EventType.TURNSTILE_OUT,
    "192.168.0.222": EventType.TURNSTILE_OUT,
    "192.168.0.220": EventType.TURNSTILE_OUT,
}

DEDUP_SECONDS = max(settings.TURNSTILE_DEDUP_SECONDS, 1)
LOCAL_TZ = timezone(timedelta(hours=5))
INITIAL_LOOKBACK_HOURS = max(settings.HIKVISION_INITIAL_LOOKBACK_HOURS, 1)
RECOVERY_OVERLAP_SECONDS = max(settings.HIKVISION_RECOVERY_OVERLAP_SECONDS, 0)
LAST_CURSOR_UTC: dict[str, datetime] = {}


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


def _find_employee_by_name(db: Session, payload_name: str) -> Employee | None:
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


def _parse_devices() -> list[dict]:
    """Parse HIKVISION_DEVICES from settings (JSON string)."""
    try:
        devices = json.loads(settings.HIKVISION_DEVICES)
        if isinstance(devices, list) and devices:
            filtered = [d for d in devices if isinstance(d, dict) and d.get("host")]
            if filtered:
                return filtered
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback to hardcoded map so polling can still recover data after downtime.
    return [{"host": ip, "name": ip, "port": 80} for ip in DEVICE_IP_MAP]


def _ensure_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_poll_window(db: Session, device_id: int, host: str) -> tuple[str, str]:
    now_local = datetime.now(LOCAL_TZ)

    latest_event = (
        db.query(Event.event_ts)
        .filter(
            Event.device_id == device_id,
            Event.event_type.in_([EventType.TURNSTILE_IN, EventType.TURNSTILE_OUT]),
        )
        .order_by(Event.event_ts.desc())
        .first()
    )

    cursor_utc = LAST_CURSOR_UTC.get(host)
    if latest_event and latest_event[0]:
        last_event_utc = _ensure_aware_utc(latest_event[0])
        if cursor_utc and cursor_utc > last_event_utc:
            last_event_utc = cursor_utc
        start_local = last_event_utc.astimezone(LOCAL_TZ) - timedelta(seconds=RECOVERY_OVERLAP_SECONDS)
    elif cursor_utc:
        start_local = cursor_utc.astimezone(LOCAL_TZ) - timedelta(seconds=RECOVERY_OVERLAP_SECONDS)
    else:
        start_local = now_local - timedelta(hours=INITIAL_LOOKBACK_HOURS)

    if start_local >= now_local:
        start_local = now_local - timedelta(minutes=1)

    start_time = start_local.strftime("%Y-%m-%dT%H:%M:%S+05:00")
    end_time = now_local.strftime("%Y-%m-%dT%H:%M:%S+05:00")
    return start_time, end_time


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


def _find_employee_by_hikvision_id(
    db: Session,
    employee_no: str,
    payload_name: str,
    host: str,
) -> Employee | None:
    """Find employee by Hikvision card/employee number.

    First tries EmployeeExternalID (system='HIKVISION'),
    then falls back to employee_no match only when name validation passes.
    Mine devices use name-based mapping to avoid ID-domain collisions.
    """
    normalized_payload_name = _normalize_name(payload_name)

    # Mine turnstiles have their own ID domain.
    # They must use explicit EmployeeExternalID mapping, never name-based runtime matching.
    if host in MINE_HOSTS:
        employee = find_employee_by_external_id(db, HIKVISION_MINE_SYSTEM, employee_no)
        if employee:
            return employee
        logger.warning(
            "[%s] Mine EmployeeExternalID mapping missing: employee_no=%s payload_name=%s system=%s",
            host,
            employee_no,
            payload_name,
            HIKVISION_MINE_SYSTEM,
        )
        return None

    # Non-mine: external ID lookup first.
    system = external_system_for_host(host) or HIKVISION_SYSTEM
    employee = find_employee_by_external_id(db, system, employee_no)
    if employee and normalized_payload_name:
        if _employee_short_name(employee) not in normalized_payload_name:
            logger.debug(
                "[%s] HIKVISION external_id name mismatch: employee_no=%s payload_name=%s mapped=%s %s",
                host,
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
            "[%s] HIKVISION employee_no name mismatch: employee_no=%s payload_name=%s mapped=%s %s",
            host,
            employee_no,
            payload_name,
            employee.last_name,
            employee.first_name,
        )
        return None
    return employee


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

    db: Session = SessionLocal()
    saved_count = 0
    try:
        device = _get_or_create_device(db, device_info)
        if not device:
            logger.error("Could not find/create device for %s", name)
            return 0
        if not device.is_active:
            logger.info("[%s] Device is disabled, skip polling", name)
            db.commit()
            return 0

        start_time, end_time = _compute_poll_window(db, device.id, host)
        events = client.fetch_access_events(start_time, end_time)
        if not events:
            db.commit()
            return 0

        max_seen_ts: datetime | None = None
        for evt_data in events:
            event_time_raw = str(evt_data.get("time", ""))
            parsed_ts = _parse_hikvision_time(event_time_raw)
            if max_seen_ts is None or parsed_ts > max_seen_ts:
                max_seen_ts = parsed_ts

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

            payload_host = str(
                evt_data.get("ipAddress")
                or evt_data.get("deviceIP")
                or evt_data.get("devIp")
                or ""
            ).strip()
            if payload_host and payload_host != host:
                logger.warning(
                    "[%s] Skipping event with mismatched payload host=%s serial=%s employee_no=%s",
                    host,
                    payload_host,
                    raw_id,
                    employee_no,
                )
                continue

            evt_payload = dict(evt_data)
            evt_payload.setdefault("source_host", host)
            evt_payload.setdefault("source_device_name", name)

            event_ts = parsed_ts
            event_type = _determine_event_type(evt_payload, host, device.name if device else name)
            payload_name = str(evt_payload.get("name", ""))
            normalized_payload_name = _normalize_name(payload_name)

            # Secondary dedup: some devices emit duplicated passages with different employeeNo/serialNo.
            # If the same name appears on the same device/type in the dedup window, keep only one record.
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
                    continue

            employee = _find_employee_by_hikvision_id(db, employee_no, payload_name, host)
            if not employee:
                logger.debug("Employee not found for Hikvision ID: %s", employee_no)
                continue

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
                source_payload=evt_payload,
            )
            db.add(event)

            try:
                db.commit()
                saved_count += 1
            except IntegrityError:
                db.rollback()  # Duplicate — skip silently

        if max_seen_ts is not None:
            LAST_CURSOR_UTC[host] = _ensure_aware_utc(max_seen_ts)

        logger.info(
            "[%s] Saved %d new events (window: %s -> %s)",
            name,
            saved_count,
            start_time,
            end_time,
        )
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
