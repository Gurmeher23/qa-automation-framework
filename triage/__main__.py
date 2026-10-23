"""CLI: ``python -m triage reports/junit.xml [--threshold 0.8]``."""

from __future__ import annotations

import argparse
import sys

from triage.cluster import DEFAULT_THRESHOLD, cluster_failures
from triage.parser import parse_junit
from triage.report import render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="triage", description="Cluster pytest JUnit failures by similarity.")
    parser.add_argument("junit_xml", help="path to a pytest --junitxml report")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="cosine similarity (0-1)")
    args = parser.parse_args(argv)
    failures = parse_junit(args.junit_xml)
    sys.stdout.write(render(cluster_failures(failures, args.threshold), len(failures)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
