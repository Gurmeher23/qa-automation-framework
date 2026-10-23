"""Read pytest's JUnit XML into :class:`Failure` objects."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from triage.models import Failure


def parse_junit(path: str | Path) -> list[Failure]:
    """Return every ``<failure>`` / ``<error>`` in the report (skips and passes are ignored)."""
    root = ET.parse(path).getroot()
    failures: list[Failure] = []
    for case in root.iter("testcase"):
        for kind in ("failure", "error"):
            node = case.find(kind)
            if node is None:
                continue
            test_id = f"{case.get('classname', '')}::{case.get('name', '')}".strip(":")
            failures.append(
                Failure(
                    test_id=test_id,
                    kind=kind,
                    message=(node.get("message") or "").strip(),
                    trace=(node.text or "").strip(),
                )
            )
    return failures
