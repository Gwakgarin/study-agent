import pytest

from src.rag_eval import contains_evidence, first_hit_rank, gate_failures, hit_rate_at_k, mean_reciprocal_rank


def test_contains_evidence_ignores_whitespace_differences():
    chunk = "정규화는 논리적\n모델링 단계에서   수행한다."
    assert contains_evidence(chunk, ["정규화는 논리적 모델링 단계에서 수행한다"])


def test_contains_evidence_matches_any_span():
    assert contains_evidence("UNION ALL은 정렬이 없다", ["없는 문장", "UNION ALL"])
    assert not contains_evidence("UNION ALL은 정렬이 없다", ["INTERSECT"])


def test_first_hit_rank_returns_first_relevant_position():
    retrieved = ["관계 없는 내용", "여기에 RANK 설명", "또 RANK 설명"]
    assert first_hit_rank(retrieved, ["RANK 설명"]) == 2


def test_first_hit_rank_is_none_when_nothing_matches():
    assert first_hit_rank(["a", "b"], ["c"]) is None


def test_first_hit_rank_with_no_evidence_never_hits():
    assert first_hit_rank(["anything"], []) is None


def test_hit_rate_at_k_counts_only_ranks_within_k():
    ranks = [1, 3, None, 6]
    assert hit_rate_at_k(ranks, 1) == 0.25
    assert hit_rate_at_k(ranks, 5) == 0.5
    assert hit_rate_at_k(ranks, 10) == 0.75


def test_mean_reciprocal_rank_treats_misses_as_zero():
    assert mean_reciprocal_rank([1, 2, None, 4]) == pytest.approx((1 + 0.5 + 0 + 0.25) / 4)


def test_metrics_on_empty_input_are_zero():
    assert hit_rate_at_k([], 5) == 0.0
    assert mean_reciprocal_rank([]) == 0.0


GATES = {
    "chunk_size": 800,
    "min_hit_at_5": 0.95,
    "min_accuracy": 0.9,
    "min_refusal_on_unanswerable": 0.85,
    "max_false_refusal": 0.05,
}


def _report(hit5=1.0, accuracy=0.95, refusal=0.9, false_refusal=0.0, answers=True):
    report = {"retrieval": [{"chunk_size": 800, "hit@5": hit5}]}
    if answers:
        report["answers"] = {
            "accuracy": accuracy,
            "refusal_on_unanswerable": refusal,
            "false_refusal_on_answerable": false_refusal,
        }
    return report


def test_gate_passes_when_every_metric_meets_its_threshold():
    assert gate_failures(_report(), GATES) == []
    assert gate_failures(_report(accuracy=0.9, refusal=0.85, false_refusal=0.05), GATES) == []


def test_gate_reports_each_missed_metric():
    failures = gate_failures(_report(hit5=0.9, refusal=0.33, false_refusal=0.08), GATES)

    assert len(failures) == 3
    assert any(f.startswith("refusal on unanswerable 33.0%") for f in failures)
    assert any(f.startswith("false refusal 8.0%") and "<=" in f for f in failures)


def test_gate_fails_when_answers_were_not_run():
    assert gate_failures(_report(answers=False), GATES) == ["answers were not evaluated (run with --answers)"]


def test_gate_fails_when_gated_chunk_size_is_missing():
    report = {"retrieval": [{"chunk_size": 300, "hit@5": 1.0}], "answers": _report()["answers"]}

    assert gate_failures(report, GATES) == ["no retrieval result for chunk_size 800"]


def test_select_questions_keeps_file_order_and_rejects_unknown_ids():
    from eval.run_eval import select_questions

    questions = [{"id": "q01"}, {"id": "q02"}, {"id": "u01"}]

    assert select_questions(questions, None) == questions
    assert select_questions(questions, ["u01", "q01"]) == [{"id": "q01"}, {"id": "u01"}]
    with pytest.raises(SystemExit):
        select_questions(questions, ["q99"])


@pytest.mark.parametrize("name", ["sqld", "holdout"])
def test_every_evidence_span_sits_inside_one_chunk(name):
    # A label that is missing from the notes, or split across two chunks, can never be
    # retrieved and would quietly count as a search miss.
    from eval.run_eval import SETS, load_chunks, load_questions

    corpus_dir, questions_path = SETS[name]
    questions = load_questions(questions_path)
    chunks = load_chunks(800, 100, corpus_dir)

    assert len({q["id"] for q in questions}) == len(questions)
    unreachable = [
        (q["id"], span)
        for q in questions
        for span in q["evidence"]
        if not any(contains_evidence(c["text"], [span]) for c in chunks)
    ]
    assert unreachable == []


def test_word_overlap_counts_shared_tokens():
    from src.rag_eval import word_overlap

    assert word_overlap("NTILE 함수", "NTILE은 행을 나눈다") == 0.5
    assert word_overlap("", "아무거나") == 0.0


def test_hard_reworded_holdout_questions_stay_reworded():
    # hr questions exist to test search on wording the notes never use; if an edit lets
    # note wording creep back in, they stop measuring that.
    from eval.run_eval import SETS, load_chunks, load_questions
    from src.rag_eval import word_overlap

    corpus_dir, questions_path = SETS["holdout"]
    chunks = load_chunks(800, 100, corpus_dir)
    hard = [q for q in load_questions(questions_path) if q["id"].startswith("hr")]

    assert len(hard) == 16
    for q in hard:
        chunk = next(c["text"] for c in chunks if contains_evidence(c["text"], q["evidence"]))
        assert word_overlap(q["question"], chunk) < 0.35, q["id"]


def test_share_is_nan_for_an_empty_group():
    import math

    from eval.run_eval import _share

    assert _share(1, [1, 2]) == 0.5
    assert math.isnan(_share(0, []))
