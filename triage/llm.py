"""Optional LLM summary via any OpenAI-compatible chat-completions endpoint.

Disabled unless ``TRIAGE_LLM=1``. Needs ``OPENAI_API_KEY``; ``OPENAI_BASE_URL``
(default ``https://api.openai.com/v1``) and ``TRIAGE_LLM_MODEL`` are optional.
Any problem (flag off, missing key, network error, bad response) returns
``None`` and the caller falls back to the offline explanation. Tests never
need a key or network.
"""

from __future__ import annotations

import os

import httpx

from triage.models import Cluster


def enabled() -> bool:
    return os.environ.get("TRIAGE_LLM") == "1" and bool(os.environ.get("OPENAI_API_KEY"))


def build_prompt(cluster: Cluster) -> str:
    """Compact prompt: a few test ids plus the representative failure, truncated."""
    tests = ", ".join(f.test_id for f in cluster.failures[:5])
    return (
        "You are a test-automation engineer. In at most 3 sentences, state the most likely common root "
        "cause of this group of test failures and what to check first.\n"
        f"Failing tests ({cluster.size}): {tests}\n"
        f"Representative failure:\n{cluster.representative.text[:1500]}"
    )


def summarise(cluster: Cluster, timeout: float = 20.0) -> str | None:
    """Ask the model; ``None`` means 'use the offline fallback'."""
    if not enabled():
        return None
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={
                "model": os.environ.get("TRIAGE_LLM_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": build_prompt(cluster)}],
                "temperature": 0,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return None
