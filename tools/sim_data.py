"""Load fixture data for sim-mode tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_fixture(fixtures_dir: Path, *parts: str) -> dict[str, Any]:
    path = fixtures_dir.joinpath(*parts)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_github_fixture(fixtures_dir: Path) -> dict[str, Any]:
    return load_fixture(fixtures_dir, "github", "evidence.json")


def load_jira_fixture(fixtures_dir: Path) -> dict[str, Any]:
    return load_fixture(fixtures_dir, "jira", "evidence.json")


def load_finops_fixture(fixtures_dir: Path) -> dict[str, Any]:
    return load_fixture(fixtures_dir, "finops", "evidence.json")


def load_tools_fixture(fixtures_dir: Path, name: str) -> dict[str, Any]:
    return load_fixture(fixtures_dir, "tools", f"{name}.json")
