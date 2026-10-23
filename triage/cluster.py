"""Group failures by TF-IDF cosine similarity of their normalised text.

No external dependencies: TF-IDF is computed over the failures of one report,
and a greedy single-pass assignment compares each failure with the first member
of every existing cluster. That is O(n * clusters) and plenty for CI-sized
reports; the greedy order is deterministic because failures keep report order.
"""

from __future__ import annotations

import math
from collections import Counter

from triage.models import Cluster, Failure
from triage.normalise import normalise, tokenise

DEFAULT_THRESHOLD = 0.8


def _tfidf_vectors(docs: list[list[str]]) -> list[dict[str, float]]:
    n = len(docs)
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))
    vectors: list[dict[str, float]] = []
    for doc in docs:
        tf = Counter(doc)
        vec = {t: (1 + math.log(c)) * (math.log((1 + n) / (1 + df[t])) + 1) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({t: v / norm for t, v in vec.items()})
    return vectors


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity of two L2-normalised sparse vectors."""
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


def cluster_failures(failures: list[Failure], threshold: float = DEFAULT_THRESHOLD) -> list[Cluster]:
    """Cluster ``failures``; larger clusters come first (ties keep report order)."""
    vectors = _tfidf_vectors([tokenise(f.text) for f in failures])
    clusters: list[Cluster] = []
    heads: list[dict[str, float]] = []
    for failure, vec in zip(failures, vectors, strict=True):
        best, best_sim = -1, 0.0
        for i, head in enumerate(heads):
            sim = cosine(vec, head)
            if sim > best_sim:
                best, best_sim = i, sim
        if best >= 0 and best_sim >= threshold:
            clusters[best].failures.append(failure)
        else:
            first_line = normalise(failure.message.splitlines()[0] if failure.message else failure.trace[:120])
            clusters.append(Cluster([failure], signature=first_line))
            heads.append(vec)
    return sorted(clusters, key=lambda c: -c.size)
