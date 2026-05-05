"""Password hashing and JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(*, subject: str, secret: str, algorithm: str, expire_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expire_minutes)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": expire}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, *, secret: str, algorithm: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        sub = payload.get("sub")
        if isinstance(sub, str):
            return sub
        return None
    except JWTError:
        return None
