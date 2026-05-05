# Database Migrations

This project now uses Alembic for schema versioning.

## Prerequisites

- Install dependencies (`pip install -r requirements.txt`).
- Ensure `DATABASE_URL` points to your target database (defaults to `sqlite:///data/aaf.db`).

## Apply migrations

```bash
alembic upgrade head
```

## Create a migration from model changes

```bash
alembic revision --autogenerate -m "add new table"
alembic upgrade head
```

## Roll back one migration

```bash
alembic downgrade -1
```

## Notes

- Baseline revision: `0001_governance_v1`.
- Alembic metadata source is `app.db.Base.metadata`; model imports are loaded in `alembic/env.py`.
- The app still supports bootstrap table creation for local-first development, but production/staging should run Alembic migrations explicitly.
