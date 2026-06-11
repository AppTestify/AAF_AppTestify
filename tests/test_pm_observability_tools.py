import asyncio

import pytest

from tools.context import ToolContext, build_tool_context
from tools.pm import check_error_rate, check_latency, check_queue_depth


@pytest.fixture
def ctx():
    from aaf.config import Settings

    return build_tool_context(Settings())


def test_pm_observability_tools_return_signals(ctx):
    for fn in (check_latency, check_error_rate, check_queue_depth):
        result = asyncio.run(fn(ctx))
        assert 0.0 <= result.signal <= 1.0
        assert result.tool_name
        assert result.evidence_lines
