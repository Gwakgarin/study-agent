import pytest

from src import tracker


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "tracker.db")


def test_get_weak_topics_empty_when_no_answers():
    assert tracker.get_weak_topics() == []


def test_topic_with_only_correct_answers_is_not_weak():
    tracker.record_answer("faiss", True)
    tracker.record_answer("faiss", True)

    assert tracker.get_weak_topics() == []


def test_topic_with_a_wrong_answer_appears_with_correct_rate():
    tracker.record_answer("faiss", True)
    tracker.record_answer("faiss", False)
    tracker.record_answer("faiss", False)

    topics = tracker.get_weak_topics()

    assert len(topics) == 1
    assert topics[0] == {
        "topic": "faiss",
        "attempts": 3,
        "wrong": 2,
        "wrong_rate": pytest.approx(2 / 3),
    }


def test_weak_topics_ordered_by_wrong_rate_desc():
    tracker.record_answer("low", False)
    tracker.record_answer("low", True)
    tracker.record_answer("low", True)
    tracker.record_answer("low", True)  # wrong_rate 0.25

    tracker.record_answer("high", False)
    tracker.record_answer("high", False)  # wrong_rate 1.0

    topics = tracker.get_weak_topics()

    assert [t["topic"] for t in topics] == ["high", "low"]


def test_get_weak_topics_respects_limit():
    for name in ["a", "b", "c"]:
        tracker.record_answer(name, False)

    assert len(tracker.get_weak_topics(limit=2)) == 2
