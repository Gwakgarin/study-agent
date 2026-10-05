import json

import pytest
from fastapi.testclient import TestClient

import server
from src import auth, projects, quizzes, sessions, tracker, usage
from tests.test_display import QUIZ, _call


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "study-agent.db"
    for module in (sessions, projects, auth, usage, quizzes, tracker):
        monkeypatch.setattr(module, "DB_PATH", db_path)
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")


@pytest.fixture
def setup(monkeypatch):
    def quiz_turn(messages, project_id):
        messages += [
            {"role": "assistant", "tool_calls": [_call("c1", "generate_quiz")]},
            {"role": "tool", "tool_call_id": "c1", "content": json.dumps(QUIZ, ensure_ascii=False)},
            {"role": "assistant", "content": "문제를 냈어요."},
        ]
        return messages

    monkeypatch.setattr(server, "run_turn", quiz_turn)
    client = TestClient(server.app)
    client.post("/api/auth/signup", json={"username": "alice", "password": "password1"})
    project_id = client.post("/api/projects", json={"name": "SQLD"}).json()["id"]
    session_id = client.post("/api/session", json={"project_id": project_id}).json()["session_id"]
    res = client.post("/api/chat", json={"session_id": session_id, "project_id": project_id, "message": "퀴즈"})
    return client, project_id, session_id, res


def _answer(client, project_id, session_id, choice, quiz_id="q1"):
    return client.post(
        "/api/quiz/answer",
        json={"session_id": session_id, "project_id": project_id, "quiz_id": quiz_id, "choice": choice},
    )


def test_chat_response_carries_quiz_card_without_answer(setup):
    _, _, _, res = setup

    card = res.json()["messages"][-1]["quiz"]

    assert card["choices"] == QUIZ["choices"]
    assert card["answered"] is None


def test_correct_choice_is_graded_and_recorded(setup):
    client, project_id, session_id, _ = setup

    card = _answer(client, project_id, session_id, 1).json()

    assert card["answered"]["correct"] is True
    assert tracker.get_weak_topics(project_id) == []
    stats = tracker.get_connection().execute("SELECT topic, correct FROM answers").fetchall()
    assert stats == [("정규화", 1)]


def test_wrong_choice_shows_answer_and_becomes_weak_topic(setup):
    client, project_id, session_id, _ = setup

    card = _answer(client, project_id, session_id, 0).json()

    assert card["answered"] == {"choice": 0, "correct": False, "answer_index": 1, "explanation": "논리적 모델링"}
    assert tracker.get_weak_topics(project_id)[0]["topic"] == "정규화"


def test_second_answer_does_not_change_the_result(setup):
    client, project_id, session_id, _ = setup
    _answer(client, project_id, session_id, 0)

    card = _answer(client, project_id, session_id, 1).json()

    assert card["answered"]["choice"] == 0
    count = tracker.get_connection().execute("SELECT COUNT(*) FROM answers").fetchone()[0]
    assert count == 1


def test_answered_state_survives_reload(setup):
    client, project_id, session_id, _ = setup
    _answer(client, project_id, session_id, 1)

    messages = server._screen(sessions.load_session(session_id))

    assert messages[-1]["quiz"]["answered"]["correct"] is True


def test_model_is_told_the_answer_was_recorded(setup):
    client, project_id, session_id, _ = setup
    _answer(client, project_id, session_id, 1)

    last = sessions.load_session(session_id)[-1]

    assert last["role"] == "system"
    assert "record_answer를 다시 부르지 마세요" in last["content"]


def test_bad_choice_and_unknown_quiz_are_rejected(setup):
    client, project_id, session_id, _ = setup

    assert _answer(client, project_id, session_id, 9).status_code == 400
    assert _answer(client, project_id, session_id, 0, quiz_id="nope").status_code == 404


def test_other_user_cannot_answer(setup):
    _, project_id, session_id, _ = setup
    other = TestClient(server.app)
    other.post("/api/auth/signup", json={"username": "bob", "password": "password1"})

    assert _answer(other, project_id, session_id, 1).status_code == 404
