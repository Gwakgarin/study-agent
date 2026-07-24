import pytest
from fastapi.testclient import TestClient

import server
from src import sessions


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "DB_PATH", tmp_path / "sessions.db")


@pytest.fixture
def client():
    return TestClient(server.app)


def _stub_run_turn(monkeypatch, reply="stub reply"):
    def fake_run_turn(messages):
        messages.append({"role": "assistant", "content": reply})
        return messages

    monkeypatch.setattr(server, "run_turn", fake_run_turn)
    return fake_run_turn


def test_create_session_returns_id_and_empty_messages(client):
    res = client.post("/api/session")

    assert res.status_code == 200
    data = res.json()
    assert data["session_id"]
    assert data["messages"] == []


def test_chat_appends_user_and_assistant_messages(client, monkeypatch):
    _stub_run_turn(monkeypatch, reply="안녕!")

    session_id = client.post("/api/session").json()["session_id"]
    res = client.post("/api/chat", json={"session_id": session_id, "message": "hi"})

    assert res.status_code == 200
    messages = res.json()["messages"]
    assert messages[-2] == {"role": "user", "content": "hi"}
    assert messages[-1] == {"role": "assistant", "content": "안녕!"}


def test_chat_history_persists_across_separate_requests(client, monkeypatch):
    """Regression test: history used to live only in an in-memory dict, lost on restart."""
    replies = iter(["first reply", "second reply"])

    def fake_run_turn(messages):
        messages.append({"role": "assistant", "content": next(replies)})
        return messages

    monkeypatch.setattr(server, "run_turn", fake_run_turn)

    session_id = client.post("/api/session").json()["session_id"]
    client.post("/api/chat", json={"session_id": session_id, "message": "first"})
    res = client.post("/api/chat", json={"session_id": session_id, "message": "second"})

    contents = [m["content"] for m in res.json()["messages"]]
    assert contents == ["first", "first reply", "second", "second reply"]

    # and it's actually durable, not just held in a local variable
    assert sessions.load_session(session_id) is not None


def test_chat_with_unknown_session_id_starts_a_fresh_conversation(client, monkeypatch):
    _stub_run_turn(monkeypatch, reply="hi there")

    res = client.post("/api/chat", json={"session_id": "never-created", "message": "hello"})

    assert res.status_code == 200
    assert res.json()["messages"][0] == {"role": "user", "content": "hello"}


def test_reset_clears_session_history(client, monkeypatch):
    _stub_run_turn(monkeypatch)

    session_id = client.post("/api/session").json()["session_id"]
    client.post("/api/chat", json={"session_id": session_id, "message": "hi"})

    res = client.post("/api/reset", json={"session_id": session_id})

    assert res.json()["messages"] == []
    assert sessions.load_session(session_id) == server.new_conversation()


def test_weak_topics_endpoint_returns_tracker_data(client, monkeypatch):
    monkeypatch.setattr(server, "get_weak_topics", lambda: [{"topic": "faiss", "wrong_rate": 0.5}])

    res = client.get("/api/weak-topics")

    assert res.status_code == 200
    assert res.json() == [{"topic": "faiss", "wrong_rate": 0.5}]


def test_weak_topics_endpoint_returns_500_on_error(client, monkeypatch):
    def boom():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(server, "get_weak_topics", boom)

    res = client.get("/api/weak-topics")

    assert res.status_code == 500
