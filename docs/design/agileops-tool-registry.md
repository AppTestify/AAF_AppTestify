# AgileOps AI Tool Registry

Canonical registry for all four governance agents (DevOps, PM, FinOps, SecOps): tool methods, API endpoints, MCP mappings, return signals, and PM scenarios.

## Single source of truth

| Artifact | Path |
|----------|------|
| Registry JSON | `data/tool_registry.json` (31 tools: 28 spec + 3 PM extensions) |
| Loader | `agents/tool_registry.py` |
| Guardrail allowlist | Derived via `registry_allowlist()` in `guardrails/tool_scope_guard.py` |

## API

```
GET /api/v1/agents/tool-registry
  ?agent=devops|project_management|finops|devsecops
  ?status=shipped|pending|roadmap|all
  ?method=direct_api|api_mcp|mcp|roadmap
```

Public read-only endpoint for workspace UI, marketing `/capabilities`, and docs.

## UI surfaces

| Surface | Route | Notes |
|---------|-------|-------|
| Workspace | `/app/tool-registry` | Full scrollable table; link from AI Config |
| Marketing | `/capabilities` | Shipped by default; toggle full registry |

Shared component: `frontend/src/components/governance/ToolRegistryTable.tsx`

## Shipped vs roadmap

- **Shipped (27):** Wired in agent `tool_callables()`, sim fixtures under `fixtures/tools/`, contract-tested in `tests/test_tool_registry_contract.py`
- **Roadmap (4):** `get_team_capacity`, `get_cost_forecast`, `get_sast_results`, `check_compliance_posture` — documented only
- **MCP Phase 3:** github-mcp / atlassian-mcp wrappers (T-068–T-070) — documented in registry, not implemented

## Related

- [CAS-71 epic](https://apptestify.atlassian.net/browse/CAS-71)
- [Phase 3 governance flow](phase-3-governance-flow.md)
