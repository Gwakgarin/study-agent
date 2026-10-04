"""Retrieval metrics for the RAG evaluation in eval/.

Each eval question carries short evidence spans copied from the notes. A retrieved
chunk counts as relevant when it contains one of those spans, so the labels stay
valid even when the chunk size changes.
"""

import re


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def contains_evidence(chunk: str, evidence: list[str]) -> bool:
    normalized = _normalize(chunk)
    return any(_normalize(span) in normalized for span in evidence)


def first_hit_rank(retrieved: list[str], evidence: list[str]) -> int | None:
    """1-based rank of the first relevant chunk, or None if none was retrieved."""
    for rank, chunk in enumerate(retrieved, start=1):
        if contains_evidence(chunk, evidence):
            return rank
    return None


def hit_rate_at_k(ranks: list[int | None], k: int) -> float:
    if not ranks:
        return 0.0
    return sum(1 for r in ranks if r is not None and r <= k) / len(ranks)


def mean_reciprocal_rank(ranks: list[int | None]) -> float:
    if not ranks:
        return 0.0
    return sum(1 / r for r in ranks if r is not None) / len(ranks)
