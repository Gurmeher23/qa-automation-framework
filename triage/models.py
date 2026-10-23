"""Plain data classes shared by the triage modules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Failure:
    """One failed or errored test case from a JUnit report."""

    test_id: str
    kind: str  # "failure" or "error"
    message: str
    trace: str

    @property
    def text(self) -> str:
        """Message and trace together: what similarity is computed on."""
        return f"{self.message}\n{self.trace}"


@dataclass
class Cluster:
    """A group of failures that very probably share one root cause."""

    failures: list[Failure] = field(default_factory=list)
    signature: str = ""  # normalised first line of the representative failure

    @property
    def size(self) -> int:
        return len(self.failures)

    @property
    def representative(self) -> Failure:
        return self.failures[0]
