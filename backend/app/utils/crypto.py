"""Symmetric encryption for sensitive credentials stored at rest.

Used for portal_credentials.encrypted_password — the automation runner must
decrypt the original password to type it into the portal login form, so a
one-way hash (bcrypt) won't work.

Generate the key once and put it in .env / Railway env as PORTAL_CRED_FERNET_KEY:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from cryptography.fernet import Fernet

from app.config import settings

# Per-key-name cache so we don't re-instantiate Fernet on every call.
# Keyed by the env-var name (e.g. "PORTAL_CRED_FERNET_KEY",
# "MASLAKA_ENCRYPTION_KEY") so distinct domains stay isolated.
_fernets: dict[str, Fernet] = {}


def _get_fernet(key_env: str = "PORTAL_CRED_FERNET_KEY") -> Fernet:
    cached = _fernets.get(key_env)
    if cached is not None:
        return cached
    raw = getattr(settings, key_env, "")
    if not raw:
        raise RuntimeError(
            f"{key_env} is not configured. "
            f"Generate one with `python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            f"and add it to your .env."
        )
    fernet = Fernet(raw.encode())
    _fernets[key_env] = fernet
    return fernet


def encrypt(plaintext: str, key_env: str = "PORTAL_CRED_FERNET_KEY") -> str:
    return _get_fernet(key_env).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str, key_env: str = "PORTAL_CRED_FERNET_KEY") -> str:
    return _get_fernet(key_env).decrypt(ciphertext.encode("utf-8")).decode("utf-8")


# ─── Bytes variants (raw XML payloads stay binary, not base64-string-wrapped) ──
# The clearinghouse payload tables store the ciphertext as LargeBinary so we
# don't pay a 33% size overhead on every XML round-trip. Use these for that.

def encrypt_bytes(plaintext: bytes, key_env: str = "PORTAL_CRED_FERNET_KEY") -> bytes:
    return _get_fernet(key_env).encrypt(plaintext)


def decrypt_bytes(ciphertext: bytes, key_env: str = "PORTAL_CRED_FERNET_KEY") -> bytes:
    return _get_fernet(key_env).decrypt(ciphertext)


def is_key_configured(key_env: str) -> bool:
    """Lightweight check used by service-init code / health endpoints."""
    return bool(getattr(settings, key_env, ""))
