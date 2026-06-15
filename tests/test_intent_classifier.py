import pytest
import time
from pm_interface.intent_classifier import classify_intent, IntentCategory

def test_intent_classifier_release_readiness():
    # Test keywords for release_readiness
    intents_and_agents = [
        classify_intent("Are we ready for release?"),
        classify_intent("deploy the app today"),
        classify_intent("ship it on monday")
    ]
    for intent, agents in intents_and_agents:
        assert intent == IntentCategory.RELEASE_READINESS
        assert set(agents) == {"devops", "project_management", "finops"}

def test_intent_classifier_delivery_health():
    # Test keywords for delivery_health
    intents_and_agents = [
        classify_intent("what is the latency?"),
        classify_intent("check error rate and health"),
        classify_intent("any sprint blockers?")
    ]
    for intent, agents in intents_and_agents:
        assert intent == IntentCategory.DELIVERY_HEALTH
        assert set(agents) == {"project_management", "devops"}

def test_intent_classifier_cost_anomaly():
    # Test keywords for cost_anomaly
    intents_and_agents = [
        classify_intent("why did our cloud cost spike?"),
        classify_intent("what is our finops spend?"),
        classify_intent("check budget anomaly")
    ]
    for intent, agents in intents_and_agents:
        assert intent == IntentCategory.COST_ANOMALY
        assert set(agents) == {"devops", "project_management", "finops"}

def test_intent_classifier_security_gate():
    # Test keywords for security_gate
    intents_and_agents = [
        classify_intent("did the security scan pass?"),
        classify_intent("any new cve?"),
        classify_intent("check for secret vulnerability")
    ]
    for intent, agents in intents_and_agents:
        assert intent == IntentCategory.SECURITY_GATE
        assert set(agents) == {"devops", "project_management", "finops", "devsecops"}

def test_intent_classifier_performance():
    # Test that classify_intent runs in <1ms
    start = time.perf_counter()
    classify_intent("deploy the app today and check security cve latency cost")
    end = time.perf_counter()
    assert (end - start) * 1000 < 1.0  # < 1ms
