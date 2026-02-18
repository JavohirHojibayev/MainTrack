import psycopg2
import sys

# Hardcoded from config.py
DB_URL = "postgresql://minetrack_user:changeme@127.0.0.1:5432/minetrack_db"

def test_connect():
    print(f"Connecting to {DB_URL}...")
    try:
        conn = psycopg2.connect(DB_URL)
        print("Connected successfully!")
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("Query executed:", cur.fetchone())
        conn.close()
    except Exception as e:
        print("Connection failed:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connect()
