"""Render clusters as text."""

from __future__ import annotations

from triage import llm
from triage.models import Cluster
from triage.summarise import explain


def render(clusters: list[Cluster], total_failures: int) -> str:
    """Grouped summary. Uses the LLM when enabled, otherwise the offline rules."""
    if not clusters:
        return "No failures found in the report."
    lines = [f"{total_failures} failing test(s) in {len(clusters)} group(s)", ""]
    for i, cluster in enumerate(clusters, 1):
        lines.append(f"[{i}] {cluster.size} test(s): {cluster.signature or '(no message)'}")
        lines.append(f"    Likely cause: {llm.summarise(cluster) or explain(cluster)}")
        for failure in cluster.failures[:8]:
            lines.append(f"      - {failure.test_id}")
        if cluster.size > 8:
            lines.append(f"      ... and {cluster.size - 8} more")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
