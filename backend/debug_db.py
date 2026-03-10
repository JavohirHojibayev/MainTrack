from __future__ import annotations

import os
import traceback

import psycopg2


def test_connect() -> None:
    db_url = os.getenv("DATABASE_URL", "postgresql://user:password@127.0.0.1:5432/db_name")
    print(f"Connecting to {db_url} ...")
    try:
        conn = psycopg2.connect(db_url)
        print("Connected successfully.")
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("Query executed:", cur.fetchone())
        conn.close()
    except Exception as exc:
        print("Connection failed:", exc)
        traceback.print_exc()


if __name__ == "__main__":
    test_connect()
