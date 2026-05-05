#!/usr/bin/env python3
"""Apply database bootstrap: tables, default tenant, superadmin, admins, optional test tenant.

Uses `.env` in the repository root (same as the API). Safe to run multiple times (idempotent).

Example:

  cd /path/to/AAF_AppTestify
  export PYTHONPATH="$(pwd)"
  python3 scripts/seed_identities.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aaf.config import get_settings  # noqa: E402
from app import db as db_mod  # noqa: E402
from app.bootstrap import bootstrap_tenancy, create_tables  # noqa: E402


def main() -> None:
    settings = get_settings()
    db_mod.init_db(settings.database_url)
    create_tables()
    db = db_mod.SessionLocal()
    try:
        bootstrap_tenancy(db, settings)
    finally:
        db.close()

    print("Bootstrap complete.")
    print(f"  Superadmin: {settings.superadmin_email}")
    print(f"  Default tenant admin: {settings.admin_email} (tenant slug: {settings.default_tenant_slug})")
    if settings.seed_test_tenant:
        print(
            f"  Test tenant: slug={settings.test_tenant_slug!r} "
            f"admin={settings.test_tenant_admin_email!r}"
        )
    else:
        print("  Test tenant seed: off (set SEED_TEST_TENANT=true in .env to enable)")


if __name__ == "__main__":
    main()
