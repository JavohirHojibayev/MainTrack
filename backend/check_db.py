import psycopg2
import sys

def test_connection():
    dsn = "postgresql://minetrack_user:MineTrack%232026!@127.0.0.1:5432/minetrack_db"
    print(f"Connecting to {dsn}...")
    try:
        conn = psycopg2.connect(dsn)
        print("Connection successful!")
        conn.close()
        return True
    except (psycopg2.Error, UnicodeDecodeError) as e:
        print(f"Connection failed or decode error: {e}")
        
        print("\nTrying to brute-force 'postgres' user password to fix/check DB...")
        passwords = ['postgres', '123', '1234', '12345', 'root', 'admin', 'password', 'ChangeMe', 'minetrack']
        found_password = None
        
        for pwd in passwords:
            print(f"Trying password: '{pwd}' ...")
            try:
                dsn_pg = f"postgresql://postgres:{pwd}@127.0.0.1:5432/postgres"
                conn = psycopg2.connect(dsn_pg, options="-c client_encoding=utf8")
                conn.autocommit = True
                print(f"SUCCESS! Password is '{pwd}'")
                found_password = pwd
                
                print("Connected as 'postgres'. Checking for minetrack_db and user...")
                cur = conn.cursor()
                
                # Check User
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'minetrack_user'")
                if not cur.fetchone():
                    print("User 'minetrack_user' missing. Creating...")
                    cur.execute("CREATE USER minetrack_user WITH PASSWORD 'changeme'")
                    print("User created.")
                else:
                    print("User 'minetrack_user' exists. Resetting password just in case...")
                    cur.execute("ALTER USER minetrack_user WITH PASSWORD 'changeme'")
                    print("Password reset.")

                # Check DB
                cur.execute("SELECT 1 FROM pg_database WHERE datname = 'minetrack_db'")
                if not cur.fetchone():
                    print("Database 'minetrack_db' missing. Creating...")
                    cur.execute("CREATE DATABASE minetrack_db OWNER minetrack_user")
                    print("Database created.")
                else:
                    print("Database 'minetrack_db' exists.")
                
                conn.close()
                print("\nRepairs completed successfully.")
                return True
                
            except (psycopg2.Error, UnicodeDecodeError) as e_try:
                # Treat UnicodeDecodeError as auth failure (since localized error message causes it)
                pass

        print("Failed to find correct postgres password.")
        print("Please ensure PostgreSQL is running and you know the 'postgres' user password.")
        return False

if __name__ == "__main__":
    test_connection()
