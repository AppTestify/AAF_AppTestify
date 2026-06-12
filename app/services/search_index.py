"""Apache OpenSearch indexing for governance entities."""

from __future__ import annotations

import logging
from typing import Any, Optional

from aaf.config import get_settings
from app.models.governance import AuditEvent, GovernanceCase, GovernanceRun

_log = logging.getLogger("aaf.search_index")


def opensearch_enabled() -> bool:
    settings = get_settings()
    return bool(settings.opensearch_enabled and settings.opensearch_url.strip())


def _client():
    from opensearchpy import OpenSearch

    settings = get_settings()
    return OpenSearch(
        hosts=[settings.opensearch_url],
        use_ssl=settings.opensearch_url.startswith("https"),
        verify_certs=False,
    )


def _index_name(entity: str) -> str:
    settings = get_settings()
    return f"{settings.opensearch_index_prefix}-{entity}-v1"


def index_document(index: str, doc_id: str, body: dict[str, Any]) -> None:
    if not opensearch_enabled():
        return
    try:
        client = _client()
        client.index(index=index, id=doc_id, body=body, refresh=False)
    except Exception:  # noqa: BLE001
        _log.exception("opensearch_index_failed", extra={"index": index, "id": doc_id})


def index_governance_run(run: GovernanceRun) -> None:
    if not opensearch_enabled():
        return
    orch = {}
    if isinstance(run.result_json, dict):
        df = run.result_json.get("decision_framing") or {}
        orch = df.get("orchestration") if isinstance(df.get("orchestration"), dict) else {}
    body = {
        "tenant_id": run.tenant_id,
        "prompt": run.prompt,
        "prompt_id": run.prompt_id,
        "status": run.status,
        "recommended_action": orch.get("recommended_action"),
        "consensus_score": orch.get("consensus_score"),
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }
    index_document(_index_name("runs"), str(run.id), body)


def index_governance_case(case: GovernanceCase) -> None:
    if not opensearch_enabled():
        return
    body = {
        "tenant_id": case.tenant_id,
        "title": case.title,
        "status": case.status,
        "latest_run_id": case.latest_run_id,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
    }
    index_document(_index_name("cases"), str(case.id), body)


def index_audit_event(event: AuditEvent) -> None:
    if not opensearch_enabled():
        return
    body = {
        "tenant_id": event.tenant_id,
        "area": event.area,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "summary": event.summary,
        "severity": event.severity,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
    index_document(_index_name("audit-events"), str(event.id), body)


def search_opensearch(
    *,
    tenant_id: Optional[int],
    query: str,
    limit: int = 50,
) -> Optional[dict[str, list[dict[str, Any]]]]:
    if not opensearch_enabled() or not query.strip():
        return None
    try:
        client = _client()
        must: list[dict[str, Any]] = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["prompt^2", "title^2", "summary", "prompt_id"],
                }
            }
        ]
        if tenant_id is not None:
            must.append({"term": {"tenant_id": tenant_id}})
        results: dict[str, list[dict[str, Any]]] = {"runs": [], "cases": [], "evidence": [], "decisions": []}
        for entity, index in (
            ("runs", _index_name("runs")),
            ("cases", _index_name("cases")),
        ):
            resp = client.search(
                index=index,
                body={"query": {"bool": {"must": must}}, "size": limit},
            )
            hits = resp.get("hits", {}).get("hits", [])
            for hit in hits:
                src = hit.get("_source") or {}
                doc_id = hit.get("_id")
                if entity == "runs":
                    results["runs"].append(
                        {
                            "id": int(doc_id) if doc_id else 0,
                            "prompt": src.get("prompt", "")[:200],
                            "status": src.get("status"),
                        }
                    )
                elif entity == "cases":
                    results["cases"].append(
                        {
                            "id": int(doc_id) if doc_id else 0,
                            "title": src.get("title"),
                            "status": src.get("status"),
                        }
                    )
        return results
    except Exception:  # noqa: BLE001
        _log.exception("opensearch_search_failed")
        return None
