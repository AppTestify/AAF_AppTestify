"""Select top 3-6 cost signals as PM-readable evidence strings."""

from __future__ import annotations

from agents.schemas import ToolResult


def package_finops_evidence(tool_results: list[ToolResult], *, max_lines: int = 6) -> list[str]:
    ranked = sorted(tool_results, key=lambda r: r.signal, reverse=True)
    lines: list[str] = []
    for result in ranked:
        for line in result.evidence_lines:
            if line not in lines:
                lines.append(line)
            if len(lines) >= max_lines:
                return lines
    return lines[:max_lines]
