from pm_interface.intent_classifier import IntentCategory, classify_pm_intent


def test_security_prompt_activates_secops():
    result = classify_pm_intent("Are there CVE vulnerabilities or secret leaks blocking release?")
    assert result.intent == IntentCategory.SECURITY_GATE
    assert "devsecops" in result.agents_needed
    assert len(result.agents_needed) == 4


def test_release_prompt_skips_secops():
    result = classify_pm_intent("Are we safe to release the current build based on GitHub CI?")
    assert result.intent == IntentCategory.RELEASE_READINESS
    assert "devsecops" not in result.agents_needed
    assert len(result.agents_needed) == 3


def test_cost_prompt():
    result = classify_pm_intent("Did cloud spend and budget variance spike this week?")
    assert result.intent == IntentCategory.COST_REVIEW
    assert "finops" in result.agents_needed


def test_observability_prompt():
    result = classify_pm_intent("Check platform health: API latency, error rate, and queue depth")
    assert result.intent == IntentCategory.OBSERVABILITY
    assert "project_management" in result.agents_needed
    assert "devops" in result.agents_needed
    assert "finops" not in result.agents_needed
    assert len(result.agents_needed) == 2
