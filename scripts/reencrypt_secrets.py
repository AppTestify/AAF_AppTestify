#!/usr/bin/env python3
"""One-time migration: re-encrypt tenant connector secrets from legacy XOR to Fernet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from aaf.config import Settings
from app import db as db_mod
from app.models.config import TenantConnectorConfig
from app.security import decrypt_json, encrypt_json, decrypt_json_legacy


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-encrypt connector secrets to Fernet")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    args = parser.parse_args()

    settings = Settings()
    db_mod.init_db(settings.database_url)
    if db_mod.SessionLocal is None:
        raise RuntimeError("Database session factory not initialized")
    key = settings.app_encryption_key
    migrated = 0
    skipped = 0

    with db_mod.SessionLocal() as db:
        rows = db.execute(select(TenantConnectorConfig)).scalars().all()
        for row in rows:
            raw = row.encrypted_credentials_json
            if not raw:
                skipped += 1
                continue
            try:
                data = decrypt_json(raw, secret=key)
            except ValueError:
                try:
                    data = decrypt_json_legacy(raw, secret=key)
                except Exception as exc:
                    print(f"SKIP {row.connector_name} tenant={row.tenant_id}: {exc}")
                    skipped += 1
                    continue
            new_cipher = encrypt_json(data, secret=key)
            if new_cipher == raw:
                skipped += 1
                continue
            print(f"MIGRATE {row.connector_name} tenant={row.tenant_id}")
            if not args.dry_run:
                row.encrypted_credentials_json = new_cipher
                migrated += 1
            else:
                migrated += 1
        if not args.dry_run:
            db.commit()

    print(f"Done: migrated={migrated} skipped={skipped} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
