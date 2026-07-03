import json
import logging
import time
from collections.abc import Callable
from typing import Any, Optional

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from app.services.llm_runtime import ActiveProvider, invoke_json_with_failover

logger = logging.getLogger(__name__)


def run_agent_llm_flow(
    agent_id: str,
    evidence_slice: list[EvidenceRecord],
    system_prompt: str,
    fallback_fn: Callable[[], AgentOpinion],
    llm_providers: list[ActiveProvider] | None = None,
) -> AgentOpinion:
    started = time.time()

    if not llm_providers:
        # Deterministic fallback
        opinion = fallback_fn()
        latency_ms = int((time.time() - started) * 1000)
        logger.info(f"Agent '{agent_id}' executed in {latency_ms}ms (mode: fallback)")
        return opinion

    # 1. Format the evidence slice
    evidence_items = []
    for e in evidence_slice:
        evidence_items.append({
            "source": e.source,
            "kind": e.kind,
            "summary": e.summary,
            "severity": e.severity,
            "metadata": e.metadata,
        })
    evidence_str = json.dumps(evidence_items, indent=2)

    # 2. Formulate user prompt
    prompt = f"""You must analyze the following evidence records and provide your professional assessment as the '{agent_id}' governance agent.

Evidence slice:
{evidence_str}

Please return your opinion as a JSON object matching the AgentOpinion schema. The schema is:
{{
  "claim": "A concise summary of your primary finding or assessment of the evidence.",
  "confidence": <float between 0.0 and 1.0 representing your confidence in this assessment>,
  "evidence_refs": [<list of strings referencing the key evidence records used, formatted as 'source:summary' or 'kind:summary'>],
  "risk_theme": "<one of 'operational_risk', 'cost_risk', 'security_risk', 'delivery_risk', 'reliability_risk', 'low_risk', 'unknown'>",
  "raw_signals": {{
     <any key numeric/structural metrics extracted from the evidence, e.g. "cost_spike_severity": 0.8>
  }}
}}

Ensure that the output is valid JSON and contains only the JSON object. Do not include markdown code block formatting like ```json or any other surrounding text.
"""

    try:
        # 3. Call LLM with failover
        response_dict, meta = invoke_json_with_failover(
            providers=llm_providers,
            prompt=prompt,
            system_prompt=system_prompt,
        )

        # 4. Parse response to AgentOpinion
        claim = str(response_dict.get("claim") or "No domain risk signals.")
        confidence = float(
            response_dict.get("confidence")
            if response_dict.get("confidence") is not None
            else 0.5
        )
        confidence = max(0.0, min(1.0, confidence))

        refs = list(response_dict.get("evidence_refs") or [])
        refs = [str(r) for r in refs][:12]
        if not refs and evidence_slice:
            # Fallback if LLM returned empty refs
            refs = [f"{e.source}:{e.summary[:40]}" for e in evidence_slice[:12]]

        theme_str = str(response_dict.get("risk_theme") or "unknown").lower()
        try:
            theme = RiskTheme(theme_str)
        except ValueError:
            theme = RiskTheme.UNKNOWN

        raw_signals = dict(response_dict.get("raw_signals") or {})

        opinion = AgentOpinion(
            agent_id=agent_id,
            claim=claim,
            confidence=round(confidence, 3),
            evidence_refs=refs,
            risk_theme=theme,
            raw_signals=raw_signals,
        )

        latency_ms = int((time.time() - started) * 1000)
        logger.info(
            f"Agent '{agent_id}' executed in {latency_ms}ms (mode: LLM, provider: {meta.get('provider')})"
        )
        return opinion

    except Exception as exc:
        logger.error(
            f"Agent '{agent_id}' LLM invocation failed, falling back to deterministic: {exc}"
        )
        opinion = fallback_fn()
        latency_ms = int((time.time() - started) * 1000)
        logger.info(
            f"Agent '{agent_id}' executed in {latency_ms}ms (mode: fallback after error)"
        )
        return opinion
