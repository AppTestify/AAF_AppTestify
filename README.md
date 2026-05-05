# AgileOps Agentic Framework (AAF)

Governance pipeline: **consensus**, **RAR**, **utility scoring**, and **explainability**, with GitHub / JIRA / FinOps connectors (simulation or live).

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/health`
- Run: `POST http://localhost:8000/api/v1/governance/run` with JSON `{"prompt":"..."}`
- Library: `GET http://localhost:8000/api/v1/prompts/library`

Set `CONNECTOR_MODE=sim` (default) for fixture-backed evidence, or `live` with the env vars in `.env.example`.

## Tests

```bash
pytest
```
