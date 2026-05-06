"""Application settings."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConnectorMode(str, Enum):
    SIM = "sim"
    LIVE = "live"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Pipeline
    tau_consensus: float = 0.55
    max_rar_loops: int = 2
    w_perf: float = 0.4
    w_cost: float = 0.3
    w_risk: float = 0.3

    # Connectors
    connector_mode: ConnectorMode = ConnectorMode.SIM
    fixtures_dir: Path = Path(__file__).resolve().parent.parent / "fixtures"
    github_token: str = ""
    github_repo: str = "owner/repo"
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    finops_cost_file: Optional[Path] = None  # JSON/CSV path for live file-based cost

    # API
    app_env: str = "dev"  # dev, staging, prod
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    api_v1_prefix: str = "/api/v1"

    # OpenTelemetry OTLP (optional). Set OTEL_EXPORTER_OTLP_ENDPOINT to enable trace + metric export.
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_headers: str = ""
    otel_service_name: str = "aaf-governance"
    otel_metric_export_interval_ms: int = 60_000

    # Prometheus text at GET /metrics without auth (for scrapers). Must stay false in production.
    metrics_public_enabled: bool = False

    # Database (SQLite default; use postgresql+psycopg://... for Postgres)
    database_url: str = "sqlite:///./data/aaf.db"

    # App-level encryption key for at-rest secret fields
    app_encryption_key: str = "change-me-32-char-encryption-key"

    # JWT auth
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Public marketing signup: creates tenant + tenant admin (disable in locked-down prod)
    public_tenant_signup_enabled: bool = False

    # Multi-tenant bootstrap (see app/bootstrap.py)
    default_tenant_slug: str = "default"
    default_tenant_name: str = "Default organization"
    superadmin_email: str = "superadmin@localhost"
    superadmin_password: str = "changeme"
    # Tenant admin on default tenant (must differ from superadmin_email)
    admin_email: str = "admin@localhost"
    admin_password: str = "changeme"

    # Optional second tenant + admin for integration / manual testing (see app/bootstrap.py)
    seed_test_tenant: bool = False
    test_tenant_slug: str = "test"
    test_tenant_name: str = "Test organization"
    test_tenant_admin_email: str = "testadmin@localhost"
    test_tenant_admin_password: str = "changeme"


def get_settings() -> Settings:
    return Settings()


def validate_runtime_safety(settings: Settings) -> None:
    """Fail fast in production when dangerous defaults are used."""
    if settings.app_env.lower() not in {"prod", "production"}:
        return
    if settings.jwt_secret.startswith("change-me") or len(settings.jwt_secret) < 24:
        raise RuntimeError("Unsafe JWT_SECRET for production")
    bad_pw = {"changeme", "password", "admin", "12345678"}
    if settings.superadmin_password.lower() in bad_pw or settings.admin_password.lower() in bad_pw:
        raise RuntimeError("Unsafe bootstrap admin password for production")
    if settings.public_tenant_signup_enabled:
        raise RuntimeError("PUBLIC_TENANT_SIGNUP_ENABLED must be false in production")
    if settings.metrics_public_enabled:
        raise RuntimeError("METRICS_PUBLIC_ENABLED must be false in production")
    if settings.app_encryption_key.startswith("change-me") or len(settings.app_encryption_key) < 24:
        raise RuntimeError("Unsafe APP_ENCRYPTION_KEY for production")
