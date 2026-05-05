import pytest

from aaf.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        tau_consensus=0.55,
        max_rar_loops=2,
        w_perf=0.4,
        w_cost=0.3,
        w_risk=0.3,
    )
