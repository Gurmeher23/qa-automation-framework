"""Unit tests for the failure-triage tool, run against a fixture JUnit report."""

from pathlib import Path

import pytest

from triage import llm
from triage.cluster import cluster_failures, cosine
from triage.models import Failure
from triage.normalise import normalise
from triage.parser import parse_junit
from triage.report import render
from triage.summarise import explain

FIXTURE = Path(__file__).parent / "fixtures" / "sample_junit.xml"


@pytest.fixture(scope="module")
def failures():
    return parse_junit(FIXTURE)


@pytest.fixture(scope="module")
def clusters(failures):
    return cluster_failures(failures)


@pytest.mark.smoke
def test_parser_reads_failures_and_errors_only(failures):
    assert len(failures) == 7
    assert sum(f.kind == "error" for f in failures) == 1
    assert all("test_logout" not in f.test_id and "skipped" not in f.test_id for f in failures)


def test_parser_keeps_message_and_trace(failures):
    first = failures[0]
    assert first.test_id == "tests.ui.test_orders::test_create_order"
    assert "Timeout 30000ms" in first.message
    assert "orders_page.py:48" in first.trace


def test_normalise_masks_noise():
    text = "obj at 0x10a1b2c30 in /home/runner/work/x/tests/a.py:48 took 30000ms id 123e4567-e89b-12d3-a456-4266141740"
    text += "00"
    out = normalise(text)
    assert "0x10a1b2c30" not in out and "/home/runner" not in out and "30000" not in out
    assert "<uuid>" in out and "a.py:N" in out


def test_same_cause_with_different_paths_and_addresses_clusters_together(clusters):
    timeouts = [c for c in clusters if "Timeout" in c.signature]
    assert len(timeouts) == 1
    assert timeouts[0].size == 3


def test_expected_group_structure(clusters):
    sizes = sorted((c.size for c in clusters), reverse=True)
    assert sizes == [3, 2, 1, 1]
    assert clusters[0].size == 3  # largest first


def test_unrelated_failures_are_not_merged(clusters):
    members = {f.test_id.split("::")[1] for c in clusters if c.size == 1 for f in c.failures}
    assert members == {"test_health", "test_login"}


def test_threshold_extremes(failures):
    assert len(cluster_failures(failures, threshold=1.01)) == len(failures)  # nothing can merge
    assert len(cluster_failures(failures, threshold=0.0)) == 1  # everything merges


def test_clustering_is_deterministic(failures):
    first = [[f.test_id for f in c.failures] for c in cluster_failures(failures)]
    second = [[f.test_id for f in c.failures] for c in cluster_failures(failures)]
    assert first == second


def test_empty_input():
    assert cluster_failures([]) == []
    assert render([], 0) == "No failures found in the report."


def test_cosine_identity():
    vec = {"a": 0.6, "b": 0.8}
    assert cosine(vec, vec) == pytest.approx(1.0)
    assert cosine(vec, {"c": 1.0}) == 0.0


@pytest.mark.parametrize(
    ("needle", "expected"),
    [
        ("Timeout", "did not appear"),
        ("401", "Authentication"),
        ("ConnectError", "unreachable"),
        ("KeyError", "Python error"),
    ],
)
def test_offline_explanation_matches_cause(clusters, needle, expected):
    cluster = next(c for c in clusters if needle in c.representative.text)
    assert expected in explain(cluster)


def test_explanation_names_most_common_location(clusters):
    timeouts = next(c for c in clusters if "Timeout" in c.signature)
    assert "orders_page.py:48" in explain(timeouts)


def test_render_groups_and_lists_tests(failures, clusters):
    text = render(clusters, len(failures))
    assert text.startswith("7 failing test(s) in 4 group(s)")
    assert "[1] 3 test(s)" in text and "test_status_filter[paid]" in text


def test_llm_disabled_by_default_and_never_calls_network(monkeypatch, clusters):
    monkeypatch.delenv("TRIAGE_LLM", raising=False)
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: pytest.fail("network must not be used"))
    assert llm.summarise(clusters[0]) is None
    assert "Likely cause:" in render(clusters, 7)


def test_llm_used_when_enabled_and_falls_back_on_error(monkeypatch, clusters):
    monkeypatch.setenv("TRIAGE_LLM", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")

    class Resp:
        def raise_for_status(self) -> None: ...
        def json(self):
            return {"choices": [{"message": {"content": "LLM says: locator drift."}}]}

    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: Resp())
    assert "LLM says" in render(clusters, 7)

    def boom(*a, **k):
        raise llm.httpx.ConnectError("offline")

    monkeypatch.setattr(llm.httpx, "post", boom)
    out = render(clusters, 7)
    assert "LLM says" not in out and "did not appear" in out


def test_failure_text_combines_message_and_trace():
    f = Failure("t::x", "failure", "msg", "trace")
    assert f.text == "msg\ntrace"
