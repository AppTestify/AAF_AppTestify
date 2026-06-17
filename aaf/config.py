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

    tau_consensus: float = 0.55
    max_rar_loops: int = 2
    rar_live_refresh_enabled: bool = True
    pipeline_phase: int = 1
    phase1_static_agents: bool = False
    max_llm_calls_per_run: int = 9
    w_perf: float = 0.4
    w_cost: float = 0.3
    w_risk: float = 0.3

    # Connectors
    connector_mode: ConnectorMode = ConnectorMode.SIM
    fixtures_dir: Path = Path(__file__).resolve().parent.parent / "fixtures"
    github_token: str = ""
    github_webhook_secret: str = ""
    github_repo: str = "owner/repo"
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project: str = "PROJ"
    jira_board_id: str = "1"
    jira_webhook_secret: str = ""
    gitlab_token: str = ""
    gitlab_project_id: str = ""
    gitlab_url: str = "https://gitlab.com"
    gitlab_webhook_secret: str = ""
    pagerduty_api_token: str = ""
    finops_cost_file: Optional[Path] = None  # JSON/CSV path for live file-based cost

    # SQLAlchemy pool tuning (optional PgBouncer sidecar in compose/helm)
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle_seconds: int = 1800

    # AWS (FinOps live tools)
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

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

    # Database (Postgres recommended for production; SQLite for local quick start)
    database_url: str = "postgresql+psycopg://aaf:aaf@localhost:5432/aaf"

    # Background jobs (Celery + Redis). Empty broker falls back to in-process thread queue.
    redis_url: str = ""
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # Apache Kafka event bus (optional; enables async webhooks + automation at scale)
    kafka_bootstrap_servers: str = ""
    kafka_enabled: bool = False
    kafka_client_id: str = "casantris-api"
    kafka_dlq_topic: str = "casantris.dlq"

    # Apache OpenSearch (optional; replaces ILIKE search when enabled)
    opensearch_url: str = ""
    opensearch_enabled: bool = False
    opensearch_index_prefix: str = "casantris"

    # Apache APISIX gateway (ops / CD smoke base URL)
    apisix_gateway_url: str = ""
    apisix_admin_url: str = ""

    # Integration execution: python (in-process) or camel (Kafka → integration worker)
    integration_mode: str = "python"

    # Evidence normalization cap per connector source
    max_evidence_per_source: int = 50

    # Input/output guardrails (see docs/design/governance-pipeline-architecture.md)
    guardrails_enabled: bool = True
    pm_prompt_max_length: int = 4000
    evidence_max_total: int = 200
    evidence_stale_hours: float = 24.0
    evidence_stale_ratio_block: float = 0.5
    max_tool_calls_per_agent: int = 5

    # App-level encryption key for at-rest secret fields
    app_encryption_key: str = "change-me-32-char-encryption-key"

    # JWT auth
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    rate_limit_max_attempts: int = 8
    rate_limit_window_minutes: int = 10

    # Signed public share links (governance run snapshot). If empty, jwt_secret is used.
    share_link_signing_secret: str = ""
    share_link_default_ttl_hours: int = 168
    # Absolute origin for share URLs in emails/Slack from background jobs (no Request), e.g. https://api.example.com
    public_share_base_url: str = ""

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


def _encryption_key_entropy_ok(key: str) -> bool:
    if len(key) < 32:
        return False
    unique = len(set(key))
    if unique < 8:
        return False
    if len(set(key[i : i + 3] for i in range(len(key) - 2))) < max(8, len(key) // 4):
        return False
    return True


def validate_runtime_safety(settings: Settings) -> None:
    """Fail fast in production when dangerous defaults are used."""
    if settings.app_env.lower() not in {"prod", "production"}:
        return
    if settings.jwt_secret.startswith("change-me") or len(settings.jwt_secret) < 32:
        raise RuntimeError("Unsafe JWT_SECRET for production")
    bad_pw = {"changeme", "password", "admin", "12345678"}
    if settings.superadmin_password.lower() in bad_pw or settings.admin_password.lower() in bad_pw:
        raise RuntimeError("Unsafe bootstrap admin password for production")
    if settings.public_tenant_signup_enabled:
        raise RuntimeError("PUBLIC_TENANT_SIGNUP_ENABLED must be false")
    if settings.metrics_public_enabled:
        raise RuntimeError("METRICS_PUBLIC_ENABLED must be false in production")
    if settings.app_encryption_key.startswith("change-me") or not _encryption_key_entropy_ok(
        settings.app_encryption_key
    ):
        raise RuntimeError("Unsafe APP_ENCRYPTION_KEY for production")
    if not (settings.celery_broker_url or settings.redis_url):
        raise RuntimeError("CELERY_BROKER_URL or REDIS_URL required in production")
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if not origins:
        raise RuntimeError("CORS_ORIGINS must be set in production")
    if "*" in origins:
        raise RuntimeError("CORS_ORIGINS must not contain wildcard in production")
    for origin in origins:
        if "localhost" in origin or "127.0.0.1" in origin:
            raise RuntimeError("CORS_ORIGINS must not include localhost in production")
