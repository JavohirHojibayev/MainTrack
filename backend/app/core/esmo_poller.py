"""
ESMO Background Poller — periodically reads medical exams from the ESMO portal.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.esmo_client import EsmoClient
from app.core.esmo_monitoring import record_poller_metrics
from app.db.session import SessionLocal
from app.models.device import Device, DeviceType
from app.models.employee import Employee
from app.models.employee_external_id import EmployeeExternalID
from app.models.event import Event, EventStatus, EventType
from app.models.medical_exam import MedicalExam

logger = logging.getLogger("esmo.poller")

ESMO_TERMINALS: list[dict[str, str]] = [
    {
        "name": "TKM 1-terminal",
        "device_code": "ESMO_TKM_1",
        "host": "192.168.8.17",
        "api_key": "351bb06ecee5549db1a79fb8703283dd",
        "model": "MT-02",
        "serial": "SN020245001",
        "profile": "Полная комплектация",
    },
    {
        "name": "TKM 2-terminal",
        "device_code": "ESMO_TKM_2",
        "host": "192.168.8.18",
        "api_key": "50624db1b29f6486d7121d2597640879",
        "model": "MT-02",
        "serial": "SN020245009",
        "profile": "Полная комплектация",
    },
    {
        "name": "TKM 3-terminal",
        "device_code": "ESMO_TKM_3",
        "host": "192.168.8.19",
        "api_key": "0862df127d6f3fd7585586e58722750c",
        "model": "MT",
        "serial": "SN020245002",
        "profile": "Полная комплектация",
    },
    {
        "name": "TKM 4-terminal",
        "device_code": "ESMO_TKM_4",
        "host": "192.168.8.20",
        "api_key": "91345b4dd27a3bbaec1a5b1476e978bc",
        "model": "MT-02",
        "serial": "SN020245004",
        "profile": "Полная комплектация",
    },
]
_TERMINALS_BY_NAME = {t["name"]: t for t in ESMO_TERMINALS}
_TERMINALS_BY_NUM = {str(i): term for i, term in enumerate(ESMO_TERMINALS, start=1)}
# ESMO portal can expose terminal IDs in bracket form: terminal [7..10].
# Map those stable IDs to approved MineTrack TKM terminals.
_TERMINAL_SLOT_TO_TKM_NUM = {
    "7": "1",
    "8": "2",
    "9": "3",
    "10": "4",
}


def get_allowed_esmo_terminal_names() -> set[str]:
    return set(_TERMINALS_BY_NAME.keys())


def _resolve_esmo_terminal(raw_terminal_name: str | None) -> dict[str, str] | None:
    if not raw_terminal_name:
        return None
    text = " ".join(raw_terminal_name.split())
    if not text:
        return None

    lowered = text.lower()
    for name, info in _TERMINALS_BY_NAME.items():
        if name.lower() in lowered:
            return info

    match = re.search(r"\bTKM\s*([1-4])\s*-\s*terminal\b", text, flags=re.IGNORECASE)
    if match:
        return _TERMINALS_BY_NUM.get(match.group(1))

    # Example: "terminal [10]" -> TKM 4-terminal
    slot_match = re.search(r"\bterminal\s*\[(\d{1,3})\]", text, flags=re.IGNORECASE)
    if slot_match:
        tkm_num = _TERMINAL_SLOT_TO_TKM_NUM.get(slot_match.group(1))
        if tkm_num:
            return _TERMINALS_BY_NUM.get(tkm_num)

    # Example from compact rows: plain "10"
    plain_num = re.fullmatch(r"\d{1,3}", text)
    if plain_num:
        tkm_num = _TERMINAL_SLOT_TO_TKM_NUM.get(plain_num.group(0))
        if tkm_num:
            return _TERMINALS_BY_NUM.get(tkm_num)
    return None


def _sync_allowed_esmo_devices(db: Session) -> int:
    """
    Force ESMO device registry to use only the 4 approved terminals.
    """
    created = 0
    now = datetime.now(timezone.utc)
    allowed_codes = {t["device_code"] for t in ESMO_TERMINALS}
    allowed_hosts = {t["host"] for t in ESMO_TERMINALS}

    for terminal in ESMO_TERMINALS:
        existing = db.query(Device).filter(Device.device_code == terminal["device_code"]).first()
        if not existing:
            existing = (
                db.query(Device)
                .filter(
                    Device.device_type == DeviceType.ESMO,
                    (Device.host == terminal["host"]) | (Device.name == terminal["name"]),
                )
                .first()
            )

        if existing:
            existing.name = terminal["name"]
            existing.device_code = terminal["device_code"]
            existing.host = terminal["host"]
            existing.device_type = DeviceType.ESMO
            existing.location = "FACTORY"
            existing.api_key = terminal["api_key"]
            existing.last_seen = now
        else:
            db.add(
                Device(
                    name=terminal["name"],
                    device_code=terminal["device_code"],
                    host=terminal["host"],
                    device_type=DeviceType.ESMO,
                    location="FACTORY",
                    api_key=terminal["api_key"],
                    is_active=True,
                    last_seen=now,
                )
            )
            created += 1

    extra_esmo_devices = (
        db.query(Device)
        .filter(
            Device.device_type == DeviceType.ESMO,
            Device.device_code != "ESMO_PORTAL",
            ~Device.device_code.in_(allowed_codes),
        )
        .all()
    )
    for device in extra_esmo_devices:
        if device.host and device.host in allowed_hosts:
            continue
        # Keep history safe: disable extra ESMO devices instead of hard delete.
        device.is_active = False

    db.flush()
    return created

def _find_employee(db: Session, pass_id: str, full_name: str) -> Optional[Employee]:
    """
    Find employee by ESMO Pass ID or Name.
    1. Check EmployeeExternalID (system='ESMO')
    2. Fallback to Employee.employee_no (if pass_id matches)
    3. Fallback to name search
    """
    if pass_id:
        # 1. External ID
        ext = db.query(EmployeeExternalID).filter(
            EmployeeExternalID.system == "ESMO",
            EmployeeExternalID.external_id == pass_id
        ).first()
        if ext:
            return db.get(Employee, ext.employee_id)
        
        # 2. Direct employee_no match
        emp = db.query(Employee).filter(Employee.employee_no == pass_id).first()
        if emp:
            return emp

    # 3. Name lookup (case-insensitive fuzzy or exact)
    if full_name:
        # Minimal: split name and check
        parts = full_name.split()
        if len(parts) >= 2:
            fscale = db.query(Employee).filter(
                Employee.last_name.ilike(f"%{parts[0]}%"),
                Employee.first_name.ilike(f"%{parts[1]}%")
            ).first()
            if fscale:
                return fscale

    return None


def _split_full_name(full_name: str) -> tuple[str, str, str | None]:
    parts = [p for p in (full_name or "").split() if p]
    if not parts:
        return "Unknown", "", None
    last_name = parts[0]
    first_name = parts[1] if len(parts) > 1 else ""
    patronymic = " ".join(parts[2:]) if len(parts) > 2 else None
    return last_name, first_name, patronymic


def _find_or_create_employee_for_esmo(db: Session, pass_id: str | None, full_name: str | None) -> Optional[Employee]:
    pass_id = (pass_id or "").strip()
    full_name = (full_name or "").strip()

    existing = _find_employee(db, pass_id, full_name)
    if existing:
        # Backfill incomplete profile fields from ESMO full name when available.
        if full_name:
            last_name, first_name, patronymic = _split_full_name(full_name)
            if patronymic and not (existing.patronymic or "").strip():
                existing.patronymic = patronymic
            if last_name and (
                not (existing.last_name or "").strip()
                or (existing.last_name or "").strip().lower() in {"unknown", "-"}
            ):
                existing.last_name = last_name
            if first_name and not (existing.first_name or "").strip():
                existing.first_name = first_name
            db.flush()
        return existing

    if not pass_id:
        return None

    # Create employee from ESMO pass card if absent in MineTrack.
    last_name, first_name, patronymic = _split_full_name(full_name)
    employee = Employee(
        employee_no=pass_id,
        first_name=first_name,
        last_name=last_name,
        patronymic=patronymic,
        is_active=True,
    )
    db.add(employee)
    db.flush()

    db.add(
        EmployeeExternalID(
            employee_id=employee.id,
            system="ESMO",
            external_id=pass_id,
        )
    )
    db.flush()
    return employee

def _parse_esmo_time_local(time_str: str) -> datetime:
    """Parse ESMO local time string to timezone-aware Asia/Tashkent(+05:00)."""
    local_tz = timezone(timedelta(hours=5))
    text = (time_str or "").strip()
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=local_tz)
        except Exception:
            continue
    return datetime.now(local_tz)


def _parse_esmo_time_utc(time_str: str) -> datetime:
    """Parse ESMO local time string and convert to UTC."""
    return _parse_esmo_time_local(time_str).astimezone(timezone.utc)


def _local_naive_to_utc(dt_local_naive: datetime) -> datetime:
    local_tz = timezone(timedelta(hours=5))
    if dt_local_naive.tzinfo is None:
        return dt_local_naive.replace(tzinfo=local_tz).astimezone(timezone.utc)
    return dt_local_naive.astimezone(timezone.utc)

def _get_or_create_esmo_device(db: Session) -> Device:
    """Ensure there is a synthetic ESMO source device for generated events."""
    device_code = "ESMO_PORTAL"
    device = db.query(Device).filter(Device.device_code == device_code).first()
    now = datetime.now(timezone.utc)
    esmo_host = urlparse(settings.ESMO_BASE_URL).hostname

    if device:
        device.last_seen = now
        if esmo_host and not device.host:
            device.host = esmo_host
        return device

    device = Device(
        name="ESMO Portal",
        device_code=device_code,
        host=esmo_host,
        device_type=DeviceType.ESMO,
        location="Medical Station",
        api_key=f"esmo_{device_code.lower()}",
        is_active=True,
        last_seen=now,
    )
    db.add(device)
    db.flush()
    return device


def _repair_recent_incomplete_exams(
    db: Session,
    client: EsmoClient,
    esmo_device_id: int,
    limit: int = 120,
) -> int:
    """
    Backfill pulse/temperature and other missing details for recent ESMO exams.
    This protects against parser/layout changes where initial ingest saved partial data.
    """
    if not client.is_logged_in and not client.login():
        return 0

    allowed_terminal_names = tuple(get_allowed_esmo_terminal_names())
    rows = (
        db.query(MedicalExam)
        .filter(
            MedicalExam.esmo_id.isnot(None),
            (
                MedicalExam.pulse.is_(None)
                | MedicalExam.temperature.is_(None)
                | MedicalExam.terminal_name.is_(None)
                | (~MedicalExam.terminal_name.in_(allowed_terminal_names))
            ),
        )
        .order_by(MedicalExam.esmo_id.desc())
        .limit(max(limit, 1))
        .all()
    )

    repaired = 0
    for exam in rows:
        esmo_id = exam.esmo_id
        if esmo_id is None:
            continue

        detail = client._fetch_exam_detail(int(esmo_id))
        if not detail:
            continue

        changed = False

        terminal_meta = _resolve_esmo_terminal(detail.get("terminal"))
        if terminal_meta and exam.terminal_name != terminal_meta["name"]:
            exam.terminal_name = terminal_meta["name"]
            changed = True

        parsed_result = (detail.get("result") or "").strip().lower()
        if parsed_result in {"passed", "failed", "review"} and exam.result != parsed_result:
            exam.result = parsed_result
            changed = True

        if detail.get("pressure_systolic") is not None and exam.pressure_systolic != detail.get("pressure_systolic"):
            exam.pressure_systolic = detail.get("pressure_systolic")
            changed = True
        if detail.get("pressure_diastolic") is not None and exam.pressure_diastolic != detail.get("pressure_diastolic"):
            exam.pressure_diastolic = detail.get("pressure_diastolic")
            changed = True
        if detail.get("pulse") is not None and exam.pulse != detail.get("pulse"):
            exam.pulse = detail.get("pulse")
            changed = True
        if detail.get("temperature") is not None and exam.temperature != detail.get("temperature"):
            exam.temperature = detail.get("temperature")
            changed = True
        if detail.get("alcohol_mg_l") is not None and exam.alcohol_mg_l != detail.get("alcohol_mg_l"):
            exam.alcohol_mg_l = detail.get("alcohol_mg_l")
            changed = True

        if changed:
            event = (
                db.query(Event)
                .filter(Event.device_id == esmo_device_id, Event.raw_id == f"esmo:{esmo_id}")
                .first()
            )
            if event:
                event.event_ts = _local_naive_to_utc(exam.timestamp)
                event.event_type = EventType.ESMO_OK if exam.result == "passed" else EventType.ESMO_FAIL

            try:
                db.commit()
                repaired += 1
            except IntegrityError:
                db.rollback()

    return repaired

def poll_esmo_once() -> int:
    """Fetch latest exams from ESMO and save to local DB."""
    if not settings.ESMO_ENABLED:
        return 0

    client = EsmoClient(
        base_url=settings.ESMO_BASE_URL,
        username=settings.ESMO_USER,
        password=settings.ESMO_PASS,
        timeout=settings.ESMO_REQUEST_TIMEOUT,
        login_retries=settings.ESMO_LOGIN_RETRIES,
    )

    probe_db: Session = SessionLocal()
    try:
        last_known_esmo_id = probe_db.query(func.max(MedicalExam.esmo_id)).scalar()
    finally:
        probe_db.close()

    exams = client.fetch_exams_since(
        since_esmo_id=last_known_esmo_id,
        max_pages=max(settings.ESMO_BACKFILL_MAX_PAGES, 1),
    )
    # Safety-net backfill: re-read recent pages and import rows missing in local DB.
    # This prevents data holes after temporary parser/layout changes or short outages.
    recent_pages = min(max(settings.ESMO_BACKFILL_MAX_PAGES, 1), 4)
    recent_candidates = client.fetch_exams_since(since_esmo_id=None, max_pages=recent_pages)
    if recent_candidates:
        candidate_ids = [int(r["esmo_id"]) for r in recent_candidates if isinstance(r.get("esmo_id"), int)]
        existing_ids: set[int] = set()
        if candidate_ids:
            probe_db2: Session = SessionLocal()
            try:
                existing_ids = {
                    int(row[0])
                    for row in probe_db2.query(MedicalExam.esmo_id).filter(MedicalExam.esmo_id.in_(candidate_ids)).all()
                    if row[0] is not None
                }
            finally:
                probe_db2.close()

        missing_recent = [r for r in recent_candidates if isinstance(r.get("esmo_id"), int) and int(r["esmo_id"]) not in existing_ids]
        merged_by_id: dict[int, dict] = {
            int(r["esmo_id"]): r for r in recent_candidates if isinstance(r.get("esmo_id"), int)
        }
        for row in exams:
            if isinstance(row.get("esmo_id"), int):
                merged_by_id[int(row["esmo_id"])] = row
        exams = sorted(merged_by_id.values(), key=lambda x: int(x.get("esmo_id") or 0), reverse=True)
        if missing_recent:
            logger.info("ESMO Poller: added %d missing rows from recent %d pages", len(missing_recent), recent_pages)

    if not exams and client.last_error:
        logger.warning("ESMO poll returned no exams: %s", client.last_error)

    if last_known_esmo_id:
        logger.info(
            "ESMO Poller: fetched %d candidate rows since esmo_id=%s",
            len(exams),
            last_known_esmo_id,
        )

    db: Session = SessionLocal()
    saved_count = 0
    repaired_count = 0
    unmatched_count = 0
    unknown_terminal_count = 0
    disabled_terminal_count = 0
    poll_error: str | None = None
    try:
        esmo_device = _get_or_create_esmo_device(db)
        created_terminal_devices = _sync_allowed_esmo_devices(db)
        db.commit()
        db.refresh(esmo_device)
        terminal_active_by_code = {
            str(d.device_code): bool(d.is_active)
            for d in db.query(Device)
            .filter(
                Device.device_type == DeviceType.ESMO,
                Device.device_code.in_([t["device_code"] for t in ESMO_TERMINALS]),
            )
            .all()
        }
        if created_terminal_devices:
            logger.info("ESMO Poller: Added %d terminal devices", created_terminal_devices)

        for ex in exams:
            esmo_id = ex.get("esmo_id")
            if not esmo_id:
                continue

            terminal_meta = _resolve_esmo_terminal(ex.get("terminal"))
            if not terminal_meta:
                unknown_terminal_count += 1
                continue
            terminal_name = terminal_meta["name"]
            terminal_code = terminal_meta["device_code"]
            if not terminal_active_by_code.get(terminal_code, True):
                disabled_terminal_count += 1
                continue

            # Find employee
            pass_id = ex.get("employee_pass_id")
            emp_name = ex.get("employee_name")
            employee = _find_or_create_employee_for_esmo(db, pass_id, emp_name)
            
            if not employee:
                logger.debug("Employee not found for ESMO exam: %s (Pass ID: %s)", emp_name, pass_id)
                unmatched_count += 1
                continue

            exam_ts_local_naive = _parse_esmo_time_local(str(ex.get("timestamp") or "")).replace(tzinfo=None)
            exam_ts_utc = _parse_esmo_time_utc(str(ex.get("timestamp") or ""))

            # Upsert medical exam record.
            existing_exam = db.query(MedicalExam).filter(MedicalExam.esmo_id == esmo_id).first()
            parsed_result = (ex.get("result") or "").strip().lower()
            if parsed_result not in {"passed", "failed", "review"}:
                if existing_exam:
                    result = existing_exam.result
                    logger.debug("ESMO Poller: keep existing result=%s for esmo_id=%s (parsed=%r)", result, esmo_id, parsed_result)
                else:
                    # Skip incomplete rows to avoid false "failed" in MainTrack.
                    logger.debug("ESMO Poller: skip incomplete exam esmo_id=%s (no reliable result)", esmo_id)
                    continue
            else:
                result = parsed_result

            if not existing_exam:
                exam_record = MedicalExam(
                    employee_id=employee.id,
                    esmo_id=esmo_id,
                    terminal_name=terminal_name,
                    result=result,
                    pressure_systolic=ex.get("pressure_systolic"),
                    pressure_diastolic=ex.get("pressure_diastolic"),
                    pulse=ex.get("pulse"),
                    temperature=ex.get("temperature"),
                    alcohol_mg_l=ex.get("alcohol_mg_l"),
                    timestamp=exam_ts_local_naive,
                )
                db.add(exam_record)
                saved_count += 1
            else:
                # Keep historical records corrected if parser improves or manual-review state appears later.
                existing_exam.employee_id = employee.id
                existing_exam.terminal_name = terminal_name
                if result:
                    existing_exam.result = result
                existing_exam.timestamp = exam_ts_local_naive
                if ex.get("pressure_systolic") is not None:
                    existing_exam.pressure_systolic = ex.get("pressure_systolic")
                if ex.get("pressure_diastolic") is not None:
                    existing_exam.pressure_diastolic = ex.get("pressure_diastolic")
                if ex.get("pulse") is not None:
                    existing_exam.pulse = ex.get("pulse")
                if ex.get("temperature") is not None:
                    existing_exam.temperature = ex.get("temperature")
                if ex.get("alcohol_mg_l") is not None:
                    existing_exam.alcohol_mg_l = ex.get("alcohol_mg_l")

            # Ensure a corresponding Event exists so access logic/reports can use it.
            event_raw_id = f"esmo:{esmo_id}"
            existing_event = (
                db.query(Event)
                .filter(Event.device_id == esmo_device.id, Event.raw_id == event_raw_id)
                .first()
            )
            if not existing_event:
                event_type = EventType.ESMO_OK if result == "passed" else EventType.ESMO_FAIL
                db.add(
                    Event(
                        device_id=esmo_device.id,
                        employee_id=employee.id,
                        event_type=event_type,
                        event_ts=exam_ts_utc,
                        raw_id=event_raw_id,
                        status=EventStatus.ACCEPTED,
                        reject_reason=None,
                        source_payload=ex,
                    )
                )
            else:
                existing_event.event_type = EventType.ESMO_OK if result == "passed" else EventType.ESMO_FAIL
                existing_event.event_ts = exam_ts_utc
                existing_event.source_payload = ex

            try:
                db.commit()
            except IntegrityError:
                db.rollback()

        repaired_count = _repair_recent_incomplete_exams(db, client, esmo_device.id)

        if saved_count > 0:
            logger.info("ESMO Poller: Saved %d new medical exams", saved_count)
        if repaired_count > 0:
            logger.info("ESMO Poller: Repaired %d recent incomplete exams", repaired_count)
        if unmatched_count > 0:
            logger.info("ESMO Poller: %d exams skipped due to missing employee mapping", unmatched_count)
        if unknown_terminal_count > 0:
            logger.info("ESMO Poller: %d exams skipped due to non-approved terminal", unknown_terminal_count)
        if disabled_terminal_count > 0:
            logger.info("ESMO Poller: %d exams skipped due to disabled terminal", disabled_terminal_count)
    except Exception as e:
        logger.error("ESMO Poller error: %s", e)
        poll_error = str(e)
        db.rollback()
    finally:
        fetched_count = len(exams)
        record_poller_metrics(
            fetched=fetched_count,
            saved=saved_count,
            repaired=repaired_count,
            unknown_terminal=unknown_terminal_count,
            unmatched=unmatched_count,
            error=poll_error,
        )
        logger.info(
            "ESMO Poller metrics: fetched=%d saved=%d repaired=%d unknown_terminal=%d unmatched=%d error=%s",
            fetched_count,
            saved_count,
            repaired_count,
            unknown_terminal_count,
            unmatched_count,
            poll_error or "none",
        )
        db.close()
    
    return saved_count + repaired_count

async def esmo_polling_loop():
    """Background async loop for ESMO polling."""
    interval = max(settings.ESMO_POLL_INTERVAL, 10)
    logger.info("ESMO Polling started (interval: %ds)", interval)
    
    while True:
        try:
            # Run blocking scrape in executor
            await asyncio.get_event_loop().run_in_executor(None, poll_esmo_once)
        except Exception as e:
            logger.error("ESMO Polling loop exception: %s", e)
        
        await asyncio.sleep(interval)
