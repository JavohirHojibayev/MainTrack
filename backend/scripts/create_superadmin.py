from __future__ import annotations

import os
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User


def main() -> None:
    username = os.getenv("SUPERADMIN_USERNAME", "admin")
    password = os.getenv("SUPERADMIN_PASSWORD", "admin123")
    role = os.getenv("SUPERADMIN_ROLE", "superadmin")

    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"User '{username}' already exists")
            return
        user = User(username=username, password_hash=get_password_hash(password), role=role, is_active=True)
        db.add(user)
        db.commit()
        print(f"Created user '{username}' with role '{role}'")
    finally:
        db.close()


if __name__ == "__main__":
    main()
