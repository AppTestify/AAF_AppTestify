"""Password hashing and JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
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


def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def encrypt_json(data: dict, *, secret: str) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    key = _derive_key(secret)
    out = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    sig = hmac.new(key, out, hashlib.sha256).hexdigest().encode("ascii")
    return base64.urlsafe_b64encode(sig + b"." + out).decode("ascii")


def decrypt_json(ciphertext: Optional[str], *, secret: str) -> dict:
    if not ciphertext:
        return {}
    payload = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
    sig, enc = payload.split(b".", 1)
    key = _derive_key(secret)
    expected = hmac.new(key, enc, hashlib.sha256).hexdigest().encode("ascii")
    if not hmac.compare_digest(sig, expected):
        raise ValueError("Invalid encrypted payload signature")
    raw = bytes(b ^ key[i % len(key)] for i, b in enumerate(enc))
    return json.loads(raw.decode("utf-8"))
