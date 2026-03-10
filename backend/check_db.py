from __future__ import annotations

import os

import psycopg2


def test_connection() -> bool:
    dsn = os.getenv("DATABASE_URL", "postgresql://user:password@127.0.0.1:5432/db_name")
    print(f"Connecting to {dsn} ...")
    try:
        conn = psycopg2.connect(dsn)
        conn.close()
        print("Connection successful.")
        return True
    except psycopg2.Error as exc:
        print(f"Connection failed: {exc}")
        return False


if __name__ == "__main__":
    raise SystemExit(0 if test_connection() else 1)

