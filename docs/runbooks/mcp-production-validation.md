# MCP Production Validation Runbook

Validate MCP (Model Context Protocol) connector configuration before enabling Phase 3 governance runs in production.

## When to run

- Before toggling **Settings → Advanced → UI preferences → `mcp_enabled: true`**
- After rotating GitHub or Jira credentials referenced by `mcp_servers.*.env_ref`
- After upgrading `@modelcontextprotocol/server-*` packages in tenant MCP config
- During post-deploy smoke checks for CAS-71 MCP transport (T-068–T-070)

## Prerequisites

- Python 3.11+ with project dependencies installed (`pip install -e ".[dev]"`)
- Optional: `mcp` package for live stdio server checks (`pip install mcp`)
- Tenant credentials in environment or `.env`:
  - `GITHUB_TOKEN` (or tenant connector secret for GitHub)
  - `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` (Atlassian MCP)
- MCP server entries in tenant UI preferences, e.g.:

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
  }
}
```

## Automated validation

From the repo root:

```bash
python scripts/validate_mcp_connectors.py
python scripts/validate_mcp_connectors.py --json
python scripts/validate_mcp_connectors.py --server github --timeout 45
```

Exit code **0** = all configured servers passed; **1** = one or more failures.

### What the script checks

1. **Config presence** — `mcp_enabled` and each `mcp_servers` entry has `command` + `args`
2. **Credential resolution** — `env_ref` maps to available tokens in the environment
3. **Session initialize** — stdio MCP client connects and completes `initialize`
4. **Tool listing** — server exposes at least one tool (sanity check for github/atlassian)
5. **Registry coverage** — AgileOps `api_mcp` tools in `data/tool_registry.json` resolve to configured servers

## Manual spot checks

After a successful governance run with MCP enabled:

1. Open **Runs → Agent Reasoning** for the run
2. Confirm agent cards show an **MCP** badge when `raw_signals.<tool>.transport === "mcp"`
3. Compare tool call counts (e.g. `DevOps 2/7`) against expected selective invocation
4. Inspect run JSON — nested tool payloads should include `"transport": "mcp"` not only `"direct_api"`

## Failure triage

| Symptom | Likely cause | Mitigation |
|---------|--------------|------------|
| `ImportError: mcp` | MCP SDK not installed in runtime image | Install `mcp` or rely on direct API fallback until image updated |
| Initialize timeout | `npx` cold start or network blocked | Increase `--timeout`; pre-warm with `npx -y @modelcontextprotocol/server-github --help` |
| Auth failure | Expired PAT or wrong `env_ref` | Re-validate connector in Settings; rotate secret |
| Tool list empty | Wrong server package version | Pin MCP server version in `args` |
| Runs show `direct_api` only | `mcp_enabled: false` or server unreachable | Enable MCP; check script output; router falls back silently |

## Rollback

Set `mcp_enabled: false` in tenant UI preferences. The transport router (`tools/mcp/router.py`) will use direct API / sim implementations without code deploy.

## Related

- [AgileOps tool registry](../design/agileops-tool-registry.md)
- [Phase 3 governance flow](../design/phase-3-governance-flow.md)
- `tests/test_mcp_transport.py` — unit tests for transport routing and fallback
