"""Symmetric encryption for sensitive credentials stored at rest.

Used for portal_credentials.encrypted_password — the automation runner must
decrypt the original password to type it into the portal login form, so a
one-way hash (bcrypt) won't work.

Generate the key once and put it in .env / Railway env as PORTAL_CRED_FERNET_KEY:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from cryptography.fernet import Fernet

from app.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        if not settings.PORTAL_CRED_FERNET_KEY:
            raise RuntimeError(
                "PORTAL_CRED_FERNET_KEY is not configured. "
                "Generate one with `python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
                "and add it to your .env."
            )
        _fernet = Fernet(settings.PORTAL_CRED_FERNET_KEY.encode())
    return _fernet


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
