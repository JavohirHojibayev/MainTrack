from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.audit import log_audit
from app.core.rbac import require_roles
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserPasswordReset

router = APIRouter()
ALLOWED_USER_ROLES = {"admin", "dispatcher", "viewer"}


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles("superadmin", "admin"))) -> list[UserOut]:
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("superadmin"))
) -> UserOut:
    normalized_role = (payload.role or "").strip().lower()
    if normalized_role not in ALLOWED_USER_ROLES:
        raise HTTPException(status_code=400, detail="Role is not allowed")

    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        role=normalized_role,
        is_active=True,
    )
    db.add(user)
    log_audit(db, current_user.id, "CREATE", "user", None, {"username": user.username, "role": user.role})
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/password", response_model=UserOut)
def reset_password(
    user_id: int,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
) -> UserOut:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    audit_changes: dict[str, str] = {"action": "update_credentials"}

    next_username = (payload.username or "").strip()
    if next_username and next_username != user.username:
        existing = db.query(User).filter(User.username == next_username, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        audit_changes["username_from"] = user.username
        audit_changes["username_to"] = next_username
        user.username = next_username

    if payload.password:
        user.password_hash = get_password_hash(payload.password)
        audit_changes["password_reset"] = "true"

    if len(audit_changes) == 1:
        raise HTTPException(status_code=400, detail="No changes provided")

    log_audit(db, current_user.id, "UPDATE", "user", user.id, audit_changes)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if (user.role or "").strip().lower() == "superadmin":
        raise HTTPException(status_code=400, detail="Cannot delete superadmin user")

    db.delete(user)
    log_audit(db, current_user.id, "DELETE", "user", user.id, {"username": user.username})
    db.commit()
