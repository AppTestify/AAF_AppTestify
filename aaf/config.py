"""Application settings."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

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
    finops_cost_file: Path | None = None  # JSON/CSV path for live file-based cost

    # API
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    api_v1_prefix: str = "/api/v1"


def get_settings() -> Settings:
    return Settings()
