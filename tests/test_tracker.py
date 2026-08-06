import pytest

from src import tracker


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "tracker.db")


def test_get_weak_topics_empty_when_no_answers():
    assert tracker.get_weak_topics("p1") == []


def test_topic_with_only_correct_answers_is_not_weak():
    tracker.record_answer("p1", "faiss", True)
    tracker.record_answer("p1", "faiss", True)

    assert tracker.get_weak_topics("p1") == []


def test_topic_with_a_wrong_answer_appears_with_correct_rate():
    tracker.record_answer("p1", "faiss", True)
    tracker.record_answer("p1", "faiss", False)
    tracker.record_answer("p1", "faiss", False)

    topics = tracker.get_weak_topics("p1")

    assert len(topics) == 1
    assert topics[0] == {
        "topic": "faiss",
        "attempts": 3,
        "wrong": 2,
        "wrong_rate": pytest.approx(2 / 3),
    }


def test_weak_topics_ordered_by_wrong_rate_desc():
    tracker.record_answer("p1", "low", False)
    tracker.record_answer("p1", "low", True)
    tracker.record_answer("p1", "low", True)
    tracker.record_answer("p1", "low", True)  # wrong_rate 0.25

    tracker.record_answer("p1", "high", False)
    tracker.record_answer("p1", "high", False)  # wrong_rate 1.0

    topics = tracker.get_weak_topics("p1")

    assert [t["topic"] for t in topics] == ["high", "low"]


def test_get_weak_topics_respects_limit():
    for name in ["a", "b", "c"]:
        tracker.record_answer("p1", name, False)

    assert len(tracker.get_weak_topics("p1", limit=2)) == 2


def test_weak_topics_are_scoped_to_project():
    tracker.record_answer("p1", "faiss", False)
    tracker.record_answer("p2", "faiss", False)

    assert len(tracker.get_weak_topics("p1")) == 1
    assert len(tracker.get_weak_topics("p2")) == 1


def _mark_due_now(project_id: str, topic: str):
    """Force a schedule row's next_review_at into the past, as if its interval had elapsed."""
    conn = tracker.get_connection()
    with conn:
        conn.execute(
            "UPDATE schedule SET next_review_at = datetime('now', '-1 day') "
            "WHERE project_id = ? AND topic = ?",
            (project_id, topic),
        )
    conn.close()


def test_due_topics_empty_before_any_answers():
    assert tracker.get_due_topics("p1") == []


def test_topic_is_not_due_immediately_after_first_answer():
    tracker.record_answer("p1", "faiss", False)

    assert tracker.get_due_topics("p1") == []


def test_topic_becomes_due_once_its_interval_has_elapsed():
    tracker.record_answer("p1", "faiss", False)
    _mark_due_now("p1", "faiss")

    due = tracker.get_due_topics("p1")

    assert [t["topic"] for t in due] == ["faiss"]


def test_correct_answer_pushes_next_review_further_out_than_wrong_answer():
    tracker.record_answer("p1", "correct-topic", True)
    tracker.record_answer("p1", "wrong-topic", False)

    # a correct first answer schedules 1 day out, a wrong answer also 1 day out —
    # but repeated correct answers should keep growing the interval, unlike wrong ones.
    tracker.record_answer("p1", "correct-topic", True)
    tracker.record_answer("p1", "correct-topic", True)
    tracker.record_answer("p1", "wrong-topic", False)

    conn = tracker.get_connection()
    row = conn.execute(
        "SELECT interval_days FROM schedule WHERE project_id = 'p1' AND topic = 'correct-topic'"
    ).fetchone()
    wrong_row = conn.execute(
        "SELECT interval_days FROM schedule WHERE project_id = 'p1' AND topic = 'wrong-topic'"
    ).fetchone()
    conn.close()

    assert row[0] > 1
    assert wrong_row[0] == 1


def test_due_topics_are_scoped_to_project():
    tracker.record_answer("p1", "faiss", False)
    tracker.record_answer("p2", "rag", False)
    _mark_due_now("p1", "faiss")
    _mark_due_now("p2", "rag")

    assert [t["topic"] for t in tracker.get_due_topics("p1")] == ["faiss"]
    assert [t["topic"] for t in tracker.get_due_topics("p2")] == ["rag"]
