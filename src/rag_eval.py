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


def gate_failures(report: dict, gates: dict) -> list[str]:
    """Compare an eval report with the thresholds in eval/gates.json.

    Returns one line per metric that missed its threshold; empty means it passed.
    """
    failures = []
    retrieval = {r["chunk_size"]: r for r in report.get("retrieval", [])}
    answers = report.get("answers")

    def check(name, value, limit, lower_is_better=False):
        missed = value > limit if lower_is_better else value < limit
        if missed:
            sign = "<=" if lower_is_better else ">="
            failures.append(f"{name} {value:.1%} (needs {sign} {limit:.0%})")

    if "min_hit_at_5" in gates:
        chunk = gates.get("chunk_size")
        if chunk not in retrieval:
            failures.append(f"no retrieval result for chunk_size {chunk}")
        else:
            check(f"Hit@5 (chunk {chunk})", retrieval[chunk]["hit@5"], gates["min_hit_at_5"])

    answer_gates = ("min_accuracy", "min_refusal_on_unanswerable", "max_false_refusal")
    if any(k in gates for k in answer_gates):
        if answers is None:
            failures.append("answers were not evaluated (run with --answers)")
        else:
            if "min_accuracy" in gates:
                check("accuracy", answers["accuracy"], gates["min_accuracy"])
            if "min_refusal_on_unanswerable" in gates:
                check("refusal on unanswerable", answers["refusal_on_unanswerable"],
                      gates["min_refusal_on_unanswerable"])
            if "max_false_refusal" in gates:
                check("false refusal", answers["false_refusal_on_answerable"], gates["max_false_refusal"],
                      lower_is_better=True)
    return failures
