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


from cryptography.fernet import Fernet, InvalidToken

def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()

def _get_fernet(secret: str) -> Fernet:
    """Derive a 32-byte url-safe base64-encoded key for Fernet from the app secret."""
    key = base64.urlsafe_b64encode(_derive_key(secret))
    return Fernet(key)

def encrypt_json(data: dict, *, secret: str) -> str:
    """Securely encrypt dict using Fernet (AES-128-CBC + HMAC-SHA256)."""
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    f = _get_fernet(secret)
    return f.encrypt(raw).decode("ascii")

def decrypt_json(ciphertext: Optional[str], *, secret: str) -> dict:
    """Decrypt Fernet ciphertext. Falls back to legacy XOR decryption if needed."""
    if not ciphertext:
        return {}
    
    f = _get_fernet(secret)
    try:
        raw = f.decrypt(ciphertext.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except InvalidToken:
        import os
        old_secret = os.environ.get("OLD_APP_ENCRYPTION_KEY")
        if old_secret:
            try:
                f_old = _get_fernet(old_secret)
                raw = f_old.decrypt(ciphertext.encode("ascii"))
                return json.loads(raw.decode("utf-8"))
            except InvalidToken:
                pass
        try:
            return decrypt_json_legacy(ciphertext, secret=secret)
        except Exception as exc:
            raise ValueError("Invalid encrypted payload or incorrect key") from exc

def encrypt_json_legacy(data: dict, *, secret: str) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    key = _derive_key(secret)
    out = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    sig = hmac.new(key, out, hashlib.sha256).hexdigest().encode("ascii")
    return base64.urlsafe_b64encode(sig + b"." + out).decode("ascii")

def decrypt_json_legacy(ciphertext: Optional[str], *, secret: str) -> dict:
    """Deprecated: Insecure XOR cipher decryption."""
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
