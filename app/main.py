"""AAF Governance API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from aaf.config import get_settings, validate_runtime_safety
from app import db as db_mod
from app.bootstrap import (
    bootstrap_tenancy,
    create_tables,
    ensure_portfolio_project_link_columns,
    ensure_tenant_notification_delivery_columns,
)
from app.db import get_engine, init_db
from app.logging_config import configure_structlog
from app.middleware.tenant_rate_limit import TenantRateLimitMiddleware
from app.routers import (
    admin_tenants,
    auth,
    governance,
    governance_intelligence,
    governance_policy,
    leads,
    metrics,
    platform_config,
    portfolio,
    governance_v1,
    prompts,
    public_share,
    rbac,
    reports,
    search,
    services_catalog,
    telemetry,
    tenant_config,
    tool_registry,
    webhooks,
)
from app.services.observability import record_request, record_span, render_prometheus, request_started
from app.services.otel import configure_otel, instrument_fastapi, shutdown_otel
from app.services.run_jobs import should_use_in_process_worker, start_worker, stop_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_structlog()
    settings = get_settings()
    validate_runtime_safety(settings)
    configure_otel(settings)
    if settings.database_url.startswith("sqlite") and ":memory:" not in settings.database_url:
        Path("data").mkdir(parents=True, exist_ok=True)
    init_db(settings.database_url)
    # Postgres production schema is owned by Alembic; SQLite dev uses create_all + legacy patches.
    if settings.database_url.startswith("sqlite"):
        create_tables()
        ensure_portfolio_project_link_columns()
        ensure_tenant_notification_delivery_columns()
    db = db_mod.SessionLocal()
    try:
        bootstrap_tenancy(db, settings)
    finally:
        db.close()
    instrument_fastapi(app)
    if should_use_in_process_worker():
        start_worker()
    else:
        _log.info("celery_broker_configured; skipping in-process governance thread worker")
    yield
    if should_use_in_process_worker():
        stop_worker()
    shutdown_otel()
    # dispose engine on shutdown (helps tests / reload)
    get_engine().dispose()


import structlog
settings = get_settings()
app = FastAPI(title="Casantris Agentic Governance Platform", version="0.1.0", lifespan=lifespan)
_log = structlog.get_logger("aaf.api")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantRateLimitMiddleware)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.time()
    request_started()
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001
        elapsed_ms = int((time.time() - start) * 1000)
        structlog.contextvars.bind_contextvars(duration_ms=elapsed_ms)
        record_request(request.method, request.url.path, 500, elapsed_ms)
        record_span(
            name=f"{request.method} {request.url.path}",
            duration_ms=elapsed_ms,
            status="error",
            attributes={"path": request.url.path, "method": request.method, "status_code": 500},
        )
        _log.exception(
            "request_failed",
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
    elapsed_ms = int((time.time() - start) * 1000)
    structlog.contextvars.bind_contextvars(duration_ms=elapsed_ms)
    record_request(request.method, request.url.path, response.status_code, elapsed_ms)
    record_span(
        name=f"{request.method} {request.url.path}",
        duration_ms=elapsed_ms,
        status="ok" if response.status_code < 500 else "error",
        attributes={"path": request.url.path, "method": request.method, "status_code": response.status_code},
    )
    response.headers["x-request-id"] = request_id
    _log.info(
        "request_complete",
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
    )
    return response

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(admin_tenants.router, prefix=settings.api_v1_prefix)
app.include_router(webhooks.router, prefix=settings.api_v1_prefix)
app.include_router(governance.router, prefix=settings.api_v1_prefix)
app.include_router(governance_intelligence.router, prefix=settings.api_v1_prefix)
app.include_router(governance_v1.router, prefix=settings.api_v1_prefix)
app.include_router(public_share.router, prefix=settings.api_v1_prefix)
app.include_router(governance_policy.router, prefix=settings.api_v1_prefix)
app.include_router(rbac.router, prefix=settings.api_v1_prefix)
app.include_router(reports.router, prefix=settings.api_v1_prefix)
app.include_router(telemetry.router, prefix=settings.api_v1_prefix)
app.include_router(prompts.router, prefix=settings.api_v1_prefix)
app.include_router(tenant_config.router, prefix=settings.api_v1_prefix)
app.include_router(platform_config.router, prefix=settings.api_v1_prefix)
app.include_router(leads.router, prefix=settings.api_v1_prefix)
app.include_router(portfolio.router, prefix=settings.api_v1_prefix)
app.include_router(metrics.router, prefix=settings.api_v1_prefix)
app.include_router(search.router, prefix=settings.api_v1_prefix)
app.include_router(services_catalog.router, prefix=settings.api_v1_prefix)
app.include_router(tool_registry.router, prefix=settings.api_v1_prefix)

# Optional production static hosting fallback for React SPA.
_dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist_dir.exists():
    assets_dir = _dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def public_prometheus_metrics(window_seconds: int = Query(default=300, ge=60, le=3600)):
    """Prometheus scrape endpoint when METRICS_PUBLIC_ENABLED=true (blocked in production)."""
    s = get_settings()
    if not s.metrics_public_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    return PlainTextResponse(render_prometheus(window_seconds=window_seconds), media_type="text/plain; version=0.0.4")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    """
    Return index.html for client-side routes when static build exists.
    Keep API and well-known backend routes untouched.
    """
    if full_path.startswith("api/") or full_path in {"health", "metrics"}:
        raise HTTPException(status_code=404, detail="Not Found")
    if not _dist_dir.exists():
        raise HTTPException(status_code=404, detail="Not Found")
    index = _dist_dir / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Not Found")
    requested = _dist_dir / full_path
    if full_path and requested.exists() and requested.is_file():
        return FileResponse(str(requested))
    return FileResponse(str(index))
