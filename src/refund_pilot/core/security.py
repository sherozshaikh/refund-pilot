"""JWT encoding/decoding and bcrypt password hashing."""

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt


def hash_password(password: str) -> str:
    """Return bcrypt hash of password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches hashed."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str, secret_key: str, algorithm: str, expire_hours: int) -> str:
    """Return signed JWT for subject."""
    expire = datetime.now(UTC) + timedelta(hours=expire_hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(token: str, secret_key: str, algorithm: str) -> dict[str, object]:
    """Decode and verify JWT, returning payload dict."""
    return dict(jwt.decode(token, secret_key, algorithms=[algorithm]))
