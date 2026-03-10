from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.event import Event
from app.models.medical_exam import MedicalExam


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {col.name: _serialize(getattr(row, col.name)) for col in row.__table__.columns}


def _write_jsonl(path: Path, rows: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_row_to_dict(row), ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Keep only current local-day data for events/medical_exams/audit_logs."
    )
    parser.add_argument("--apply", action="store_true", help="Apply deletion (default is dry-run).")
    parser.add_argument(
        "--backup-on-dry-run",
        action="store_true",
        help="Also write backup files during dry-run mode.",
    )
    parser.add_argument(
        "--tz-offset-hours",
        type=int,
        default=5,
        help="Local timezone offset hours used for day boundary (default: 5).",
    )
    parser.add_argument(
        "--backup-dir",
        default="db/archives",
        help="Backup directory for removed rows (JSONL files).",
    )
    args = parser.parse_args()

    tz_local = timezone(timedelta(hours=args.tz_offset_hours))
    now_local = datetime.now(tz_local)
    day_start_local_aware = datetime(now_local.year, now_local.month, now_local.day, tzinfo=tz_local)
    day_start_local_naive = day_start_local_aware.replace(tzinfo=None)

    backup_root = Path(args.backup_dir) / now_local.strftime("%Y-%m-%d")
    stamp = now_local.strftime("%Y%m%d_%H%M%S")

    db = SessionLocal()
    try:
        old_events_q = db.query(Event).filter(Event.event_ts < day_start_local_aware)
        old_exams_q = db.query(MedicalExam).filter(MedicalExam.timestamp < day_start_local_naive)
        old_audits_q = db.query(AuditLog).filter(AuditLog.ts < day_start_local_aware)

        old_events = old_events_q.order_by(Event.id.asc()).all()
        old_exams = old_exams_q.order_by(MedicalExam.id.asc()).all()
        old_audits = old_audits_q.order_by(AuditLog.id.asc()).all()

        print(f"day_start_local={day_start_local_aware.isoformat()}")
        print(f"old_events={len(old_events)}")
        print(f"old_medical_exams={len(old_exams)}")
        print(f"old_audit_logs={len(old_audits)}")

        should_backup = args.apply or args.backup_on_dry_run
        if should_backup:
            if old_events:
                _write_jsonl(backup_root / f"{stamp}_events_old.jsonl", old_events)
            if old_exams:
                _write_jsonl(backup_root / f"{stamp}_medical_exams_old.jsonl", old_exams)
            if old_audits:
                _write_jsonl(backup_root / f"{stamp}_audit_logs_old.jsonl", old_audits)
            print(f"backup_dir={backup_root}")
        else:
            print("backup_dir=skipped (dry-run)")

        if not args.apply:
            print("dry_run=true (no delete)")
            return 0

        deleted_events = old_events_q.delete(synchronize_session=False)
        deleted_exams = old_exams_q.delete(synchronize_session=False)
        deleted_audits = old_audits_q.delete(synchronize_session=False)
        db.commit()

        print("dry_run=false")
        print(f"deleted_events={deleted_events}")
        print(f"deleted_medical_exams={deleted_exams}")
        print(f"deleted_audit_logs={deleted_audits}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
