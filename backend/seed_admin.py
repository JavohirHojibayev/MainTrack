import sys
import os
sys.path.append(os.getcwd())

from app.db.session import engine
from app.db.base import Base
import app.models  # noqa: F401 — import all models so they register with Base

print("Creating all missing tables...")
Base.metadata.create_all(bind=engine)
print("Tables created (or already existed).")

# Now seed admin user
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
try:
    username = "admin"
    password = "admin"

    print(f"Checking for user '{username}'...")
    user = db.query(User).filter(User.username == username).first()

    if user:
        print(f"User '{username}' found. Updating password...")
        user.password_hash = get_password_hash(password)
        user.is_active = True
        if not user.role:
            user.role = "admin"
        print("Password updated.")
    else:
        print(f"User '{username}' not found. Creating...")
        user = User(
            username=username,
            password_hash=get_password_hash(password),
            role="admin",
            is_active=True
        )
        db.add(user)
        print("User created.")

    db.commit()
    print("Done! Login: admin / admin")
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
