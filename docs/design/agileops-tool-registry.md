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

- **Shipped (31):** All registry tools wired in agent `tool_callables()` except none remaining roadmap; contract-tested in `tests/test_tool_registry_contract.py`
- **MCP Phase 3 (T-068–T-070):** `tools/mcp/` transport layer routes 9 `api_mcp` tools through external github-mcp / atlassian-mcp servers with direct API fallback

### MCP tenant configuration

Set in **Settings → Advanced → UI preferences**:

```json
{
  "mcp_enabled": true,
  "mcp_servers": {
    "github": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env_ref": "github_token"
    },
    "atlassian": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-atlassian"],
      "env_ref": "jira_credentials"
    }
  },
  "team_capacity": { "available_hours": 320, "planned_hours": 380, "leave_count": 3 },
  "sast": { "org": "myorg", "project_key": "myproject", "api_token": "<token>" }
}
```

Tool results include `raw_signals.transport`: `sim` | `direct_api` | `mcp`.

## Related

- [CAS-71 epic](https://apptestify.atlassian.net/browse/CAS-71)
- [Phase 3 governance flow](phase-3-governance-flow.md)
