from datetime import datetime, timedelta, timezone
import uuid
import jwt
import logging
import hashlib
import hmac
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models.user import User

logger = logging.getLogger(__name__)

try:
    from passlib.context import CryptContext  # type: ignore

    _HAS_PASSLIB = True
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    _HAS_PASSLIB = False
    pwd_context = None


def _hash_password(password: str) -> str:
    if _HAS_PASSLIB:
        try:
            return pwd_context.hash(password)
        except Exception as exc:
            # Fallback for dev-only if bcrypt backend is broken
            logger.warning("passlib hash failed; using dev fallback: %s", exc)
            return hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    if _HAS_PASSLIB:
        try:
            return pwd_context.verify(password, password_hash)
        except Exception as exc:
            logger.warning("passlib verify failed; using dev fallback: %s", exc)
            return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), password_hash)
    return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), password_hash)

ROLE_INHERITANCE = {
    "clinician": {"clinician"},
    "senior_clinician": {"senior_clinician", "clinician"},
    "admin": {"admin", "senior_clinician", "clinician"},
    "audit_viewer": {"audit_viewer"},
}


def ensure_default_admin(db: Session) -> None:
    settings = get_settings()
    if not _HAS_PASSLIB and settings.ENVIRONMENT != "dev":
        raise RuntimeError("passlib is required outside dev environment")
    if not _HAS_PASSLIB:
        logger.warning("passlib not installed; using insecure hash for dev only")
    existing = db.query(User).filter(User.username == settings.DEV_ADMIN_USERNAME).first()
    if existing:
        return
    user = User(
        username=settings.DEV_ADMIN_USERNAME,
        role="admin",
        password_hash=_hash_password(settings.DEV_ADMIN_PASSWORD),
        force_password_change=settings.DEV_ADMIN_FORCE_CHANGE,
    )
    db.add(user)
    db.commit()


def authenticate_dev_stub(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not _verify_password(password, user.password_hash):
        return None
    if _HAS_PASSLIB and not user.password_hash.startswith("$2"):
        user.password_hash = _hash_password(password)
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    return user


def create_access_token(user: User) -> str:
    settings = get_settings()
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set")
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    if settings.AUTH_MODE != "dev_stub":
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OIDC not wired")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def role_allows(user_role: str, required_role: str) -> bool:
    return required_role in ROLE_INHERITANCE.get(user_role, set())


def require_role(required_role: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not role_allows(user.role, required_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency
