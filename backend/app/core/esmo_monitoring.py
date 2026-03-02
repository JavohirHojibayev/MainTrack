from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc

from app.core.config import settings
from app.core.esmo_client import EsmoClient
from app.db.session import SessionLocal
from app.models.medical_exam import MedicalExam

logger = logging.getLogger("esmo.monitoring")


_lock = threading.Lock()

_poller_metrics: dict[str, Any] = {
    "last_run_at": None,
    "last": {
        "fetched": 0,
        "saved": 0,
        "repaired": 0,
        "unknown_terminal": 0,
        "unmatched": 0,
        "error": None,
    },
    "totals": {
        "runs": 0,
        "fetched": 0,
        "saved": 0,
        "repaired": 0,
        "unknown_terminal": 0,
        "unmatched": 0,
        "errors": 0,
    },
}

_health_state: dict[str, Any] = {
    "checked_at": None,
    "status": "not_started",
    "message": "Health check not started",
    "n": 0,
    "portal_latest_ids": [],
    "db_latest_ids": [],
    "missing_in_db": [],
    "unexpected_in_db": [],
    "latest_gap": None,
    "error": None,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_poller_metrics(
    *,
    fetched: int,
    saved: int,
    repaired: int,
    unknown_terminal: int,
    unmatched: int,
    error: str | None = None,
) -> None:
    with _lock:
        _poller_metrics["last_run_at"] = _now_iso()
        _poller_metrics["last"] = {
            "fetched": int(fetched),
            "saved": int(saved),
            "repaired": int(repaired),
            "unknown_terminal": int(unknown_terminal),
            "unmatched": int(unmatched),
            "error": error,
        }

        totals = _poller_metrics["totals"]
        totals["runs"] += 1
        totals["fetched"] += int(fetched)
        totals["saved"] += int(saved)
        totals["repaired"] += int(repaired)
        totals["unknown_terminal"] += int(unknown_terminal)
        totals["unmatched"] += int(unmatched)
        if error:
            totals["errors"] += 1



def get_poller_metrics() -> dict[str, Any]:
    with _lock:
        return {
            "last_run_at": _poller_metrics["last_run_at"],
            "last": dict(_poller_metrics["last"]),
            "totals": dict(_poller_metrics["totals"]),
        }



def _query_db_latest_ids(n: int) -> list[int]:
    db = SessionLocal()
    try:
        rows = (
            db.query(MedicalExam.esmo_id)
            .filter(MedicalExam.esmo_id.isnot(None))
            .order_by(desc(MedicalExam.esmo_id))
            .limit(max(n, 1))
            .all()
        )
        return [int(row[0]) for row in rows if row[0] is not None]
    finally:
        db.close()



def _query_portal_latest_ids(n: int, max_pages: int) -> list[int]:
    client = EsmoClient(
        base_url=settings.ESMO_BASE_URL,
        username=settings.ESMO_USER,
        password=settings.ESMO_PASS,
        timeout=settings.ESMO_REQUEST_TIMEOUT,
        login_retries=settings.ESMO_LOGIN_RETRIES,
    )
    rows = client.fetch_exams_since(since_esmo_id=None, max_pages=max(max_pages, 1))
    ids = sorted({int(r["esmo_id"]) for r in rows if isinstance(r.get("esmo_id"), int)}, reverse=True)
    return ids[: max(n, 1)]



def run_esmo_health_check(*, n: int | None = None, max_pages: int | None = None) -> dict[str, Any]:
    sample_n = max(int(n or settings.ESMO_HEALTHCHECK_LAST_N), 1)
    pages = max(int(max_pages or settings.ESMO_HEALTHCHECK_MAX_PAGES), 1)

    try:
        portal_ids = _query_portal_latest_ids(sample_n, pages)
        db_ids = _query_db_latest_ids(sample_n)

        portal_set = set(portal_ids)
        db_set = set(db_ids)

        missing_in_db = [exam_id for exam_id in portal_ids if exam_id not in db_set]
        unexpected_in_db = [exam_id for exam_id in db_ids if exam_id not in portal_set]

        latest_gap = None
        if portal_ids and db_ids:
            latest_gap = int(portal_ids[0]) - int(db_ids[0])

        status = "ok"
        message = "ESMO and MainTrack latest IDs are aligned"
        if not portal_ids:
            status = "degraded"
            message = "ESMO health-check: portal returned no IDs"
        elif missing_in_db:
            status = "degraded"
            message = f"Missing {len(missing_in_db)} IDs in MainTrack from latest {sample_n}"

        result: dict[str, Any] = {
            "checked_at": _now_iso(),
            "status": status,
            "message": message,
            "n": sample_n,
            "portal_latest_ids": portal_ids,
            "db_latest_ids": db_ids,
            "missing_in_db": missing_in_db,
            "unexpected_in_db": unexpected_in_db,
            "latest_gap": latest_gap,
            "error": None,
        }
    except Exception as exc:
        result = {
            "checked_at": _now_iso(),
            "status": "error",
            "message": "ESMO health-check failed",
            "n": sample_n,
            "portal_latest_ids": [],
            "db_latest_ids": [],
            "missing_in_db": [],
            "unexpected_in_db": [],
            "latest_gap": None,
            "error": str(exc),
        }

    with _lock:
        _health_state.clear()
        _health_state.update(result)

    if result["status"] == "ok":
        logger.info(
            "ESMO HealthCheck: status=ok n=%d latest_gap=%s",
            result["n"],
            result["latest_gap"],
        )
    else:
        logger.warning(
            "ESMO HealthCheck: status=%s message=%s missing=%d error=%s",
            result["status"],
            result["message"],
            len(result.get("missing_in_db") or []),
            result.get("error"),
        )

    return result



def get_esmo_health_state() -> dict[str, Any]:
    with _lock:
        return dict(_health_state)


async def esmo_healthcheck_loop() -> None:
    interval = max(settings.ESMO_HEALTHCHECK_INTERVAL_SECONDS, 60)
    logger.info(
        "ESMO HealthCheck loop started (interval: %ds, n=%d)",
        interval,
        settings.ESMO_HEALTHCHECK_LAST_N,
    )

    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(None, run_esmo_health_check)
        except Exception as exc:
            logger.error("ESMO HealthCheck loop exception: %s", exc)

        await asyncio.sleep(interval)
