"""Offline, rule-based explanation of what a cluster of failures most likely means."""

from __future__ import annotations

import re
from collections import Counter

from triage.models import Cluster

# (regex over failure text, explanation). First match wins; order is most specific first.
_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"strict mode violation", re.I),
     "A locator matches several elements. Make the locator more specific (role, test id, exact text)."),
    (re.compile(r"(Timeout \d+ms exceeded|TimeoutError).*(waiting for|locator|expect)", re.I | re.S),
     "A UI element did not appear or change in time. Check whether the page changed, a previous step "
     "silently failed, or the environment is slow. Look at the attached trace before adding waits."),
    (re.compile(r"Connection(Refused|Error)|ConnectError|Connection refused|Name or service not known", re.I),
     "The application under test was unreachable. Environment or deployment problem, not a test bug."),
    (re.compile(r"\b(401|403)\b.*(!=|==)|Not authenticated|Admin role required", re.I | re.S),
     "Authentication or authorisation failed. Check the test account, session handling, or a changed role rule."),
    (re.compile(r"\b5\d\d\b.*(!=|==)|Internal Server Error", re.I | re.S),
     "The server returned a 5xx. Look at the application log for the same time window; this is likely a product bug."),
    (re.compile(r"\b422\b", re.I),
     "Validation behaviour differs from the test's expectation. Check whether the API contract changed."),
    (re.compile(r"assert .* (==|!=|in|not in) ", re.I),
     "Expected and actual values differ. If many tests show the same diff, a product behaviour or "
     "shared test data changed."),
    (re.compile(r"AssertionError", re.I),
     "An assertion failed. Compare expected and actual in the report; the failure is in the checked behaviour."),
    (re.compile(r"(KeyError|AttributeError|TypeError|NameError)", re.I),
     "A Python error inside the test or helper code. Likely a test-code bug or a changed response shape."),
]


def _common_frame(cluster: Cluster) -> str | None:
    """Most frequent ``file.py:N`` location across the cluster's tracebacks."""
    frames: Counter[str] = Counter()
    for f in cluster.failures:
        frames.update(set(re.findall(r"([\w/.-]+\.py):(\d+)", f.trace)))
    if not frames:
        return None
    (path, line), _ = frames.most_common(1)[0]
    return f"{path}:{line}"


def _match(text: str) -> str | None:
    return next((why for pattern, why in _RULES if pattern.search(text)), None)


def explain(cluster: Cluster) -> str:
    """Return a one-paragraph, human-readable guess at the common cause."""
    rep = cluster.representative
    # The message is the most reliable signal; fall back to the full trace only when it is silent.
    cause = _match(rep.message) or _match(rep.text)
    cause = cause or "No known pattern. Start from the first line of the traceback."
    frame = _common_frame(cluster)
    where = f" Most common location: {frame}." if frame else ""
    return f"{cause}{where} Affects {cluster.size} test(s)."
