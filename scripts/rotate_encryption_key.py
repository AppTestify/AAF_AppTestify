#!/usr/bin/env python3
"""Re-encrypt secrets when APP_ENCRYPTION_KEY rotates (supports OLD_APP_ENCRYPTION_KEY grace window)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from aaf.config import Settings
from app.db import SessionLocal, init_db
from app.models.config import TenantConnectorConfig, TenantSettings
from app.security import decrypt_json, encrypt_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    new_key = os.environ.get("APP_ENCRYPTION_KEY", Settings().app_encryption_key)
    old_key = os.environ.get("OLD_APP_ENCRYPTION_KEY", "")
    if not old_key:
        print("Set OLD_APP_ENCRYPTION_KEY for rotation, or use reencrypt_secrets.py for same-key migration")
        return 1

    settings = Settings()
    init_db(settings.database_url)
    count = 0
    with SessionLocal() as db:
        for model, field in (
            (TenantConnectorConfig, "encrypted_credentials_json"),
            (TenantSettings, "llm_keys_encrypted_json"),
        ):
            rows = db.execute(select(model)).scalars().all()
            for row in rows:
                raw = getattr(row, field)
                if not raw:
                    continue
                data = decrypt_json(raw, secret=old_key)
                new_cipher = encrypt_json(data, secret=new_key)
                if not args.dry_run:
                    setattr(row, field, new_cipher)
                count += 1
        if not args.dry_run:
            db.commit()
    print(f"Rotated {count} encrypted blobs dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
