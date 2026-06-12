import pytest

from aaf.config import Settings
from guardrails.tool_scope_guard import check_tool_call


@pytest.mark.asyncio
async def test_tool_scope_blocks_excess_calls():
    settings = Settings(guardrails_enabled=True, max_tool_calls_per_agent=5)
    for idx in range(5):
        result = check_tool_call("devops", "get_ci_status", call_index=idx, settings=settings)
        assert result.passed
    blocked = check_tool_call("devops", "get_ci_status", call_index=5, settings=settings)
    assert blocked.blocked

