from connectors.evidence_normalizer import normalize_all


def test_normalize_github_fixture():
    raw = {
        "github": {
            "pull_requests": [{"title": "fix", "state": "open", "draft": False, "number": 1}],
            "workflow_runs": [{"name": "ci", "conclusion": "failure", "id": 1}],
            "issues": [],
        }
    }
    out = normalize_all(raw)
    assert any(r.kind == "workflow_run" for r in out)
    assert any(r.severity > 0.5 for r in out)
