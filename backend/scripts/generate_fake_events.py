from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests


def main() -> None:
    base_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    api_key = os.getenv("API_KEY", "")
    device_code = os.getenv("DEVICE_CODE", "TURNSTILE-1")
    employee_no = os.getenv("EMPLOYEE_NO", "E1001")

    if not api_key:
        print("API_KEY env is required")
        return

    now = datetime.now(timezone.utc)

    events = [
        {
            "device_code": device_code,
            "raw_id": f"{device_code}-t1",
            "event_type": "TURNSTILE_IN",
            "event_ts": (now - timedelta(minutes=30)).isoformat(),
            "employee_no": employee_no,
        },
        {
            "device_code": device_code,
            "raw_id": f"{device_code}-m1",
            "event_type": "MINE_IN",
            "event_ts": (now - timedelta(minutes=20)).isoformat(),
            "employee_no": employee_no,
        },
        {
            "device_code": device_code,
            "raw_id": f"{device_code}-e1",
            "event_type": "ESMO_OK",
            "event_ts": (now - timedelta(minutes=25)).isoformat(),
            "employee_no": employee_no,
            "payload": {"bp": "120/80", "temp": 36.6},
        },
        {
            "device_code": device_code,
            "raw_id": f"{device_code}-t2",
            "event_type": "TOOL_TAKE",
            "event_ts": (now - timedelta(minutes=15)).isoformat(),
            "employee_no": employee_no,
        },
        {
            "device_code": device_code,
            "raw_id": f"{device_code}-m2",
            "event_type": "MINE_IN",
            "event_ts": (now - timedelta(minutes=10)).isoformat(),
            "employee_no": employee_no,
        },
        {
            "device_code": device_code,
            "raw_id": f"{device_code}-m3",
            "event_type": "MINE_OUT",
            "event_ts": (now - timedelta(minutes=2)).isoformat(),
            "employee_no": employee_no,
        },
        {
            "device_code": device_code,
            "raw_id": f"{device_code}-t3",
            "event_type": "TOOL_RETURN",
            "event_ts": (now - timedelta(minutes=1)).isoformat(),
            "employee_no": employee_no,
        },
    ]

    url = f"{base_url}/api/v1/events/ingest"
    resp = requests.post(url, json={"events": events}, headers={"X-API-Key": api_key}, timeout=10)
    resp.raise_for_status()
    print(resp.json())


if __name__ == "__main__":
    main()
