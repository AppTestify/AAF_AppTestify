# AAF Gap Analysis & Competitor Research
_Generated: June 2026_

---

## 1. Critical Security Gaps

### 1.1 Homemade XOR Cipher (HIGH RISK)
**File:** `app/security.py` — `encrypt_json` / `decrypt_json`

The credential encryption uses XOR with a SHA-256-derived key. XOR is not encryption — it leaks key material, is trivially reversible with known plaintext, and breaks entirely against repeated keys. Connector credentials and LLM API keys are encrypted with this scheme.

**Fix:** Replace with `cryptography.fernet.Fernet` (AES-128-CBC + HMAC) or AES-GCM. One-line swap:
```python
from cryptography.fernet import Fernet
```

### 1.2 JWT in sessionStorage (MEDIUM RISK)
**File:** `frontend/src/authStorage.ts`

Tokens are stored in `sessionStorage`, which is accessible to any JavaScript on the page. An XSS vulnerability anywhere in the React app can silently exfiltrate the JWT.

**Fix:** Use `httpOnly; Secure; SameSite=Strict` cookies set by the API. Remove `authStorage.ts` entirely.

### 1.3 In-Memory Rate Limiter (MEDIUM RISK)
**File:** `app/routers/auth.py` — `_FAILED: dict`

The login brute-force limiter (`_MAX_LOGIN_ATTEMPTS = 8`) lives in a process-local dict. It resets on every restart and does not work across Gunicorn workers or multiple replicas.

**Fix:** Back with Redis (`slowapi` + Redis) or a DB table with a short-TTL index.

### 1.4 No Token Refresh Mechanism
Access tokens are issued with no refresh flow. Expired tokens log the user out with no recovery path. No `exp` claim is surfaced to the frontend for pre-emptive renewal.

**Fix:** Issue short-lived access tokens + a long-lived refresh token (httpOnly cookie). Add `POST /api/v1/auth/refresh`.

---

## 2. Architecture & Core Logic Gaps

### 2.1 Agents Are Heuristic Rules, Not AI
**Files:** `agents/devops.py`, `agents/sre.py`, `agents/finops.py`, `agents/devsecops.py`, `agents/pm_agent.py`

All five agents use hardcoded if/else threshold logic against severity floats. No agent calls an LLM or performs semantic reasoning. The "agentic" framing is misleading — this is a rule engine dressed as a multi-agent system.

**Gap vs competitors:** Port, LinearB, and Cortex route real LLM calls per agent context. The pipeline LLM call happens only at the final explanation step in AAF.

**Fix:** Give each agent a dedicated LLM prompt with its domain role. The deterministic fallback can stay for degraded mode.

### 2.2 RAR Loop Amplifies, Never Adds New Signal
**File:** `connectors/evidence_normalizer.py` — `enrich_for_rar`

Re-Grounded Agentic Reasoning (RAR) is supposed to fetch new context when consensus is low. In practice, `enrich_for_rar` just duplicates high-severity records with +0.08 severity and a label prefix. It cannot converge on genuinely new information because it never calls any external source.

**Fix:** On RAR trigger, fetch live connector data (already wired as `live_refresh_evidence` but only used when `rar_live_refresh_enabled=True`), or invoke a clarifying LLM sub-call with the conflicting opinions as context.

### 2.3 Dual Consensus Implementations Out of Sync
Two separate consensus algorithms exist:
- `orchestrator/consensus.py` — weighted dominant-theme + conflict-pair penalty
- `app/services/agentic_intelligence.py` — simple average confidence

They produce different scores from the same inputs and are used in different API paths. The governance intelligence dashboard (`/intelligence`) can show different consensus numbers than the pipeline output.

**Fix:** Consolidate to one `consensus` module; import it from both paths.

### 2.4 Connector Routing Is Naive Keyword Regex
**File:** `pm_interface/router.py`

Connectors are selected by regex keyword match on the PM's prompt. "azure" triggers only FinOps, but Azure is equally relevant to SRE and DevOps. A prompt about "deployment stability" matches nothing and falls back to all three connectors.

**Fix:** Use embedding-based semantic routing, or at minimum expand the regex vocabulary and add a "route all if ambiguous" policy with connector priority weighting.

### 2.5 Agents Run Synchronously
**File:** `agents/registry.py` — `run_all_agents`

All five agents execute sequentially in a single synchronous call. With real LLM backends this would add 5× per-agent latency to every pipeline run.

**Fix:** `asyncio.gather` across async agent callables with per-agent timeout.

### 2.6 JIRA Project Hardcoded
**File:** `app/services/governance_service.py`

```python
ctx = {"prompt": prompt, "github_repo": settings.github_repo, "jira_project": "PROJ"}
```

`"PROJ"` is hardcoded. Tenants with differently-keyed projects get wrong Jira queries.

**Fix:** Add `jira_project_key` to tenant connector config and read it at runtime.

### 2.7 No Evidence Pagination or Size Cap
The normalizer returns every PR, workflow run, and Jira issue without limit. A repo with 500 open PRs produces 500 EvidenceRecords fed into every agent — blowing up LLM context windows and adding latency with no marginal value.

**Fix:** Add a `max_evidence_per_source` config (default 50) applied in `normalize_all`.

---

## 3. Feature Gaps vs Competitors

### 3.1 No DORA Metrics
LinearB, Sleuth, Faros, and Harness all track the four DORA metrics (deployment frequency, lead time for changes, change failure rate, mean time to recovery) as first-class entities. AAF has no deployment tracking, no change failure rate, and no MTTR measurement.

**Impact:** PM and engineering leader personas — the primary target users — expect DORA as table stakes in 2026.

### 3.2 No GitLab / Bitbucket Support
Only GitHub is supported (`github_connector.py`, `github_live.py`). All major competitors support GitLab, Bitbucket, and Azure DevOps Repos. Enterprises running on GitLab Self-Managed are excluded.

### 3.3 No Real-Time Webhook / Event Ingestion
Evidence is fetched synchronously when a governance run is triggered. There is no webhook listener to react to CI failures, PR merges, or Jira status changes as they happen.

**Competitors:** LinearB WorkerB bot reacts to GitHub events in real time. Port triggers agentic workflows from webhook events.

### 3.4 No Slack / Teams Notifications
User notifications are email-only (`app/services/email_runtime.py`). The governance decision lifecycle (cases, approvals, decisions) produces no chat notifications.

**Competitors:** LinearB WorkerB nudges developers in Slack about stale PRs. Port has native Slack and Teams integrations.

### 3.5 No Software Catalog / Service Ownership
Cortex and Port are built around a software catalog: every microservice has an owner, a scorecard, and production-readiness checks. AAF has a portfolio model (projects + releases) but no concept of a service, its dependencies, SLOs, or owning team.

### 3.6 No Streaming for Long-Running Governance Runs
Governance runs return a single JSON blob on completion. There's no SSE or WebSocket stream for real-time progress (agent opinions populating as they resolve, RAR loop status, etc.).

### 3.7 Limited AI Provider Support in Practice
The code supports OpenAI, Anthropic, Azure OpenAI, and AWS Bedrock configuration, but there's no Ollama / self-hosted model support, no model-routing based on task type (cheap model for classification, expensive for explanation), and no cost tracking per LLM call against a budget.

### 3.8 No Observability for AI Decisions
There is an explainability index (XI score) but no structured logging of LLM prompt/response pairs for auditing, no latency tracking per-provider, and no hallucination detection layer.

**Competitor context:** Harness SEI tracks AI coding tool ROI at the token level per PR.

---

## 4. Testing Gaps

| Area | Current State | Gap |
|---|---|---|
| Agent unit tests | None | No tests for each agent with diverse evidence sets |
| Pipeline integration | `test_pipeline_integration.py` — 17 lines, no LLM mock | No test for RAR triggering, LLM fallback, streaming |
| Connector live mode | Not tested | No tests for GitHub/Jira live connector error paths |
| Security | `test_security_runtime.py` — 29 lines | No tests for XOR decryption correctness, JWT expiry, rate limit reset |
| Frontend | Zero tests | No component tests, no E2E (Playwright/Cypress) |
| Load / performance | `scripts/load_test.py` (script only) | No automated load test in CI |

Total test lines: **1,221** across 18 files — reasonable coverage for auth/API routes but thin for core ML/agent logic.

---

## 5. Competitor Benchmark Summary

| Feature | AAF | LinearB | Faros AI | Port.io | Cortex | Sleuth |
|---|---|---|---|---|---|---|
| Multi-agent governance | ✅ (rules) | Partial | Partial | ✅ (LLM) | Scorecard | ❌ |
| DORA metrics | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GitHub connector | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GitLab connector | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Jira connector | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Real-time webhooks | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Slack / Teams | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Software catalog | ❌ | ❌ | Partial | ✅ | ✅ | ❌ |
| LLM per agent | ❌ | N/A | Partial | ✅ | ❌ | ❌ |
| Explainability index | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| RAR / consensus loop | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| AI cost tracking | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| SOC2 / compliance reports | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Token refresh | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multi-tenant | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

**AAF's defensible differentiators:** Explainability index (XI), RAR consensus loop, and the PM-centric governance narrative are genuinely novel. No competitor has this combination.

**AAF's biggest gaps:** DORA metrics, real-time event ingestion, secure encryption, and LLM-backed agents — all of which competitors offer as baseline features.

---

## 6. Priority Remediation Roadmap

### P0 (Ship blockers)
1. Replace XOR cipher with Fernet — credentials are at risk today
2. Move JWT to httpOnly cookie — XSS exposure
3. Fix in-memory rate limiter to use DB or Redis

### P1 (Core product quality)
4. Add DORA metric tracking (deployment frequency, lead time, CFR, MTTR)
5. Give each agent a real LLM call with domain-specific prompt + deterministic fallback
6. Fix RAR enrichment to use live connector refresh by default
7. Unify the two consensus implementations

### P2 (Competitive parity)
8. GitLab and Bitbucket connectors
9. Webhook ingestion endpoint for GitHub/Jira events
10. Slack / Teams notification integration
11. Streaming SSE for governance run progress
12. Evidence pagination / max-per-source cap

### P3 (Differentiation & enterprise)
13. Software catalog model (service → owner → SLO → scorecard)
14. LLM cost tracking per governance run
15. SOC2 control mapping evidence export
16. E2E test suite (Playwright)
17. Async parallel agent execution

---

_Sources: [LinearB Gartner Magic Quadrant 2026](https://markets.financialcontent.com/wral/article/bizwire-2026-5-11-linearb-named-a-leader-in-the-2026-gartner-magic-quadrant-for-developer-productivity-insight-platforms) · [Cortex Engineering Intelligence Platforms](https://www.cortex.io/post/engineering-intelligence-platforms-definition-benefits-tools) · [Port Agentic SDLC Platform](https://www.port.io/blog/port-agentic-engineering-platform) · [Harness AI ROI tools](https://www.computerweekly.com/blog/CW-Developer-Network/Harness-tightens-up-AI-ROI-spend-with-new-tools) · [Sleuth DORA Metrics Guide](https://www.sleuth.io/resources/dora-metrics-complete-guide/)_
