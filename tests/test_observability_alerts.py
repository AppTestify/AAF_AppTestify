from app.services.observability import _evaluate_alert_rules


def test_dead_letter_alert_triggers():
    rules = _evaluate_alert_rules(
        {"error_rate": 0.0, "latency_ms_p95": 0.0, "run_queue_depth": 0},
        {"state": "ok", "long_burn_rate": 0.0},
        dead_letter_count=1,
    )
    dl = next(r for r in rules if r["id"] == "governance_run_dead_letter")
    assert dl["triggered"] is True
    assert dl["severity"] == "warning"
