from connectors.evidence_normalizer import normalize_all


def test_normalize_github_fixture():
    raw = {
        "github": {
            "owner": "apptestify",
            "repo": "payment-service",
            "pull_requests": [
                {
                    "title": "fix",
                    "state": "open",
                    "draft": False,
                    "number": 1,
                    "html_url": "https://github.com/apptestify/payment-service/pull/1",
                }
            ],
            "workflow_runs": [
                {
                    "name": "ci",
                    "conclusion": "failure",
                    "id": 1,
                    "html_url": "https://github.com/apptestify/payment-service/actions/runs/1",
                }
            ],
            "issues": [],
        }
    }
    out = normalize_all(raw)
    assert any(r.kind == "workflow_run" for r in out)
    assert any(r.severity > 0.5 for r in out)
    pr = next(r for r in out if r.kind == "open_pr")
    assert pr.metadata.get("url") == "https://github.com/apptestify/payment-service/pull/1"
    wf = next(r for r in out if r.kind == "workflow_run")
    assert wf.metadata.get("url") == "https://github.com/apptestify/payment-service/actions/runs/1"


def test_normalize_jira_includes_browse_url_and_key_prefix():
    raw = {
        "jira": {
            "_base_url": "https://apptestify.atlassian.net",
            "issues": [
                {
                    "key": "PAY-441",
                    "fields": {"summary": "Blocked deploy", "status": {"name": "Blocked"}},
                }
            ],
        }
    }
    out = normalize_all(raw)
    issue = next(r for r in out if r.source == "jira")
    assert issue.summary.startswith("PAY-441:")
    assert issue.metadata.get("url") == "https://apptestify.atlassian.net/browse/PAY-441"
