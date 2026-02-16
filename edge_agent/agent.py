from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

import requests


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS buffered_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_id TEXT NOT NULL UNIQUE,
            payload TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0,
            created_ts TEXT NOT NULL
        )
        """
    )
    conn.commit()


def buffer_events(conn: sqlite3.Connection, events: list[dict[str, Any]]) -> None:
    for event in events:
        raw_id = event.get("raw_id")
        if not raw_id:
            continue
        try:
            conn.execute(
                "INSERT INTO buffered_events (raw_id, payload, sent, created_ts) VALUES (?, ?, 0, ?)",
                (raw_id, json.dumps(event), datetime.now(timezone.utc).isoformat()),
            )
        except sqlite3.IntegrityError:
            continue
    conn.commit()


def load_events_file(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_unsent(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT id, payload FROM buffered_events WHERE sent = 0 ORDER BY id ASC LIMIT ?", (limit,)
    )
    rows = cur.fetchall()
    result = []
    for row_id, payload in rows:
        data = json.loads(payload)
        data["_buffer_id"] = row_id
        result.append(data)
    return result


def mark_sent(conn: sqlite3.Connection, ids: list[int]) -> None:
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    conn.execute(f"UPDATE buffered_events SET sent = 1 WHERE id IN ({placeholders})", ids)
    conn.commit()


def send_batch(config: dict[str, Any], events: list[dict[str, Any]]) -> bool:
    if not events:
        return True
    url = f"{config['backend_url']}/api/v1/events/ingest"
    payload = {"events": [{k: v for k, v in e.items() if k != "_buffer_id"} for e in events]}
    headers = {"X-API-Key": config["api_key"]}
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    return True


def main() -> None:
    config_path = os.getenv("EDGE_AGENT_CONFIG", "config.json")
    config = load_config(config_path)

    conn = sqlite3.connect(config.get("sqlite_path", "buffer.db"))
    try:
        init_db(conn)
        events = load_events_file(config.get("events_file", "events.json"))
        buffer_events(conn, events)

        backoff = 2
        while True:
            batch = get_unsent(conn, int(config.get("batch_size", 50)))
            if not batch:
                print("No pending events")
                break
            try:
                send_batch(config, batch)
                mark_sent(conn, [e["_buffer_id"] for e in batch])
                backoff = 2
                print(f"Sent {len(batch)} events")
            except requests.exceptions.HTTPError as exc:
                if exc.response.status_code == 401:
                    print("Authentication failed (401). Please check API Key. Exiting...")
                    break
                print(f"Send failed: {exc}. Retrying in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
            except Exception as exc:
                print(f"Send failed: {exc}. Retrying in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
