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


def test_normalize_pagerduty_high_urgency_unresolved():
    """High urgency + unresolved incident -> severity 0.9"""
    raw = {
        "pagerduty": {
            "incidents": [
                {
                    "id": "INC001",
                    "title": "Payment service down",
                    "status": "triggered",
                    "urgency": "high",
                    "html_url": "https://apptestify.pagerduty.com/incidents/INC001",
                    "created_at": "2026-06-17T12:00:00Z",
                    "resolved_at": None,
                    "mttr_hours": None,
                }
            ]
        }
    }
    out = normalize_all(raw)
    incident = next(r for r in out if r.source == "pagerduty")
    assert incident.kind == "incident"
    assert incident.summary == "Payment service down"
    assert incident.severity == 0.9  # 0.75 (high) + 0.15 (triggered)
    assert incident.metadata.get("status") == "triggered"
    assert incident.metadata.get("urgency") == "high"
    assert incident.metadata.get("url") == "https://apptestify.pagerduty.com/incidents/INC001"


def test_normalize_pagerduty_medium_urgency_acknowledged():
    """Medium urgency + acknowledged incident -> severity 0.65"""
    raw = {
        "pagerduty": {
            "incidents": [
                {
                    "id": "INC002",
                    "title": "Database connection issues",
                    "status": "acknowledged",
                    "urgency": "medium",
                    "html_url": "https://apptestify.pagerduty.com/incidents/INC002",
                    "created_at": "2026-06-17T11:00:00Z",
                    "resolved_at": None,
                }
            ]
        }
    }
    out = normalize_all(raw)
    incident = next(r for r in out if r.source == "pagerduty")
    assert incident.severity == 0.65  # 0.50 (medium) + 0.15 (acknowledged)


def test_normalize_pagerduty_low_urgency_resolved():
    """Low urgency + resolved incident -> severity 0.3"""
    raw = {
        "pagerduty": {
            "incidents": [
                {
                    "id": "INC003",
                    "title": "Minor monitoring alert",
                    "status": "resolved",
                    "urgency": "low",
                    "resolved_at": "2026-06-17T13:30:00Z",
                    "mttr_hours": 1.5,
                }
            ]
        }
    }
    out = normalize_all(raw)
    incident = next(r for r in out if r.source == "pagerduty")
    assert incident.severity == 0.3  # 0.30 (low) + 0.0 (resolved, no +0.15)
    assert incident.metadata.get("mttr_hours") == 1.5


def test_normalize_pagerduty_missing_fields():
    """Incident with missing optional fields -> graceful defaults"""
    raw = {
        "pagerduty": {
            "incidents": [
                {
                    "id": "INC004",
                    # title missing, use "Incident"
                    "status": "triggered",
                    # urgency missing, default to low (0.3)
                }
            ]
        }
    }
    out = normalize_all(raw)
    incident = next(r for r in out if r.source == "pagerduty")
    assert incident.summary == "Incident"
    assert incident.severity == 0.45  # 0.30 (low default) + 0.15 (triggered)


def test_normalize_pagerduty_multiple_incidents():
    """Multiple incidents are normalized separately with correct severities"""
    raw = {
        "pagerduty": {
            "incidents": [
                {
                    "id": "INC001",
                    "title": "Critical outage",
                    "status": "triggered",
                    "urgency": "high",
                },
                {
                    "id": "INC002",
                    "title": "Non-critical issue",
                    "status": "resolved",
                    "urgency": "low",
                },
            ]
        }
    }
    out = normalize_all(raw)
    pd_recs = [r for r in out if r.source == "pagerduty"]
    assert len(pd_recs) == 2
    high_sev = next(r for r in pd_recs if r.metadata.get("id") == "INC001")
    low_sev = next(r for r in pd_recs if r.metadata.get("id") == "INC002")
    assert high_sev.severity > low_sev.severity


def test_normalize_pagerduty_empty_incidents():
    """Empty incidents list -> no records generated"""
    raw = {"pagerduty": {"incidents": []}}
    out = normalize_all(raw)
    pd_recs = [r for r in out if r.source == "pagerduty"]
    assert len(pd_recs) == 0


def test_normalize_pagerduty_with_other_sources():
    """PagerDuty normalizer works alongside other sources"""
    raw = {
        "github": {
            "owner": "apptestify",
            "repo": "payment-service",
            "pull_requests": [],
            "workflow_runs": [],
            "issues": [],
        },
        "pagerduty": {
            "incidents": [
                {
                    "id": "INC001",
                    "title": "Service degraded",
                    "status": "triggered",
                    "urgency": "high",
                }
            ]
        },
    }
    out = normalize_all(raw)
    github_recs = [r for r in out if r.source == "github"]
    pd_recs = [r for r in out if r.source == "pagerduty"]
    assert len(pd_recs) == 1
    assert any(r.kind == "incident" for r in pd_recs)


def test_normalize_pagerduty_severity_bounds():
    """Severity values are always within [0.0, 1.0]"""
    raw = {
        "pagerduty": {
            "incidents": [
                {
                    "id": "INC001",
                    "title": "Test",
                    "status": "triggered",
                    "urgency": "high",
                }
            ]
        }
    }
    out = normalize_all(raw)
    incident = next(r for r in out if r.source == "pagerduty")
    assert 0.0 <= incident.severity <= 1.0

