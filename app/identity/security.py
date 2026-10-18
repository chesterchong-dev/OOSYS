"""Password hashing and opaque, revocable bearer-session primitives."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = _password_hash.hash("oosys-dummy-password-not-valid")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return _password_hash.verify(password, encoded)
    except (ValueError, TypeError):
        return False


def issue_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def opaque_key(value: str, secret: str | None = None) -> str:
    """Return a keyed digest so stored rate-limit keys cannot be cheaply reversed."""
    key = (secret or "oosys-development-only-rate-limit-key").encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def session_expiry(hours: int = 12) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
