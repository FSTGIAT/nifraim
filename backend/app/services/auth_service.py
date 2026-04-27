from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    user_id: str,
    role: str = "agent",
    agency_id: str | None = None,
) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload: dict = {"sub": user_id, "exp": expire, "role": role}
    if agency_id:
        payload["agency_id"] = agency_id
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_impersonation_token(
    target_user_id: str,
    parent_user_id: str,
    parent_role: str,
    agency_id: str,
) -> str:
    """Short-lived agent-scope JWT minted by an agency super-user drilling into one of their agents.

    The token authenticates AS the target agent (sub = target_user_id) so existing
    agent endpoints work unchanged, but carries an `impersonator` claim so the
    frontend can show a banner and the backend can audit/restrict if needed.
    """
    expire = datetime.utcnow() + timedelta(minutes=15)
    payload = {
        "sub": target_user_id,
        "exp": expire,
        "role": "agent",
        "impersonator": parent_user_id,
        "impersonator_role": parent_role,
        "agency_id": agency_id,
    }
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
    """Return the user_id (sub) from an agent JWT, or None for invalid/portal tokens."""
    payload = decode_token_full(token)
    return payload.get("sub") if payload else None


def decode_token_full(token: str) -> dict | None:
    """Return the full agent JWT payload (with role/agency_id/impersonator), or None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") == "portal":
            return None  # Portal tokens cannot be used as agent tokens
        return payload
    except Exception:
        return None
