"""Deterministic domain agents."""

__all__ = ["run_all_agents"]


def __getattr__(name: str):
    if name == "run_all_agents":
        from agents.registry import run_all_agents

        return run_all_agents
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
