from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_portal_token(portal_token: str, user_id: str) -> str:
    """Create a short-lived JWT for portal access (4 hours)."""
    expire = datetime.utcnow() + timedelta(hours=4)
    payload = {"sub": portal_token, "user_id": user_id, "type": "portal", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_portal_token(token: str) -> dict | None:
    """Decode a portal JWT. Returns {"sub": portal_token, "user_id": ...} or None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "portal":
            return None
        return payload
    except Exception:
        return None


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") == "portal":
            return None  # Portal tokens cannot be used as agent tokens
        return payload.get("sub")
    except Exception:
        return None
