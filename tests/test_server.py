import json

import pytest
from fastapi.testclient import TestClient

import server
from src import projects, sessions


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "study-agent.db"
    monkeypatch.setattr(sessions, "DB_PATH", db_path)
    monkeypatch.setattr(projects, "DB_PATH", db_path)
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")


@pytest.fixture
def client():
    return TestClient(server.app)


def _stub_run_turn(monkeypatch, reply="stub reply"):
    def fake_run_turn(messages, project_id):
        messages.append({"role": "assistant", "content": reply})
        return messages

    monkeypatch.setattr(server, "run_turn", fake_run_turn)
    return fake_run_turn


def test_create_project_returns_id_and_name(client):
    res = client.post("/api/projects", json={"name": "생물학"})

    assert res.status_code == 200
    data = res.json()
    assert data["id"]
    assert data["name"] == "생물학"


def test_list_projects_returns_created_projects(client):
    client.post("/api/projects", json={"name": "생물학"})
    client.post("/api/projects", json={"name": "화학"})

    res = client.get("/api/projects")

    assert res.status_code == 200
    assert [p["name"] for p in res.json()] == ["생물학", "화학"]


def test_create_session_returns_id_and_empty_messages(client):
    res = client.post("/api/session", json={"project_id": "p1"})

    assert res.status_code == 200
    data = res.json()
    assert data["session_id"]
    assert data["messages"] == []


def test_create_session_injects_due_topics_greeting(client, monkeypatch):
    monkeypatch.setattr(
        server, "get_due_topics", lambda project_id: [{"topic": "faiss", "next_review_at": "..."}]
    )

    res = client.post("/api/session", json={"project_id": "p1"})

    messages = res.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert "faiss" in messages[0]["content"]


def test_chat_appends_user_and_assistant_messages(client, monkeypatch):
    _stub_run_turn(monkeypatch, reply="안녕!")

    session_id = client.post("/api/session", json={"project_id": "p1"}).json()["session_id"]
    res = client.post("/api/chat", json={"session_id": session_id, "project_id": "p1", "message": "hi"})

    assert res.status_code == 200
    messages = res.json()["messages"]
    assert messages[-2] == {"role": "user", "content": "hi"}
    assert messages[-1] == {"role": "assistant", "content": "안녕!"}


def test_chat_history_persists_across_separate_requests(client, monkeypatch):
    """Regression test: history used to live only in an in-memory dict, lost on restart."""
    replies = iter(["first reply", "second reply"])

    def fake_run_turn(messages, project_id):
        messages.append({"role": "assistant", "content": next(replies)})
        return messages

    monkeypatch.setattr(server, "run_turn", fake_run_turn)

    session_id = client.post("/api/session", json={"project_id": "p1"}).json()["session_id"]
    client.post("/api/chat", json={"session_id": session_id, "project_id": "p1", "message": "first"})
    res = client.post("/api/chat", json={"session_id": session_id, "project_id": "p1", "message": "second"})

    contents = [m["content"] for m in res.json()["messages"]]
    assert contents == ["first", "first reply", "second", "second reply"]

    # and it's actually durable, not just held in a local variable
    assert sessions.load_session(session_id) is not None


def test_chat_with_unknown_session_id_starts_a_fresh_conversation(client, monkeypatch):
    _stub_run_turn(monkeypatch, reply="hi there")

    res = client.post(
        "/api/chat", json={"session_id": "never-created", "project_id": "p1", "message": "hello"}
    )

    assert res.status_code == 200
    assert res.json()["messages"][0] == {"role": "user", "content": "hello"}


def test_reset_clears_session_history(client, monkeypatch):
    _stub_run_turn(monkeypatch)

    session_id = client.post("/api/session", json={"project_id": "p1"}).json()["session_id"]
    client.post("/api/chat", json={"session_id": session_id, "project_id": "p1", "message": "hi"})

    res = client.post("/api/reset", json={"session_id": session_id, "project_id": "p1"})

    assert res.json()["messages"] == []
    assert sessions.load_session(session_id) == server.new_conversation()


def test_weak_topics_endpoint_returns_tracker_data(client, monkeypatch):
    monkeypatch.setattr(
        server, "get_weak_topics", lambda project_id: [{"topic": "faiss", "wrong_rate": 0.5}]
    )

    res = client.get("/api/weak-topics", params={"project_id": "p1"})

    assert res.status_code == 200
    assert res.json() == [{"topic": "faiss", "wrong_rate": 0.5}]


def test_weak_topics_endpoint_returns_500_on_error(client, monkeypatch):
    def boom(project_id):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(server, "get_weak_topics", boom)

    res = client.get("/api/weak-topics", params={"project_id": "p1"})

    assert res.status_code == 500


def test_list_notes_returns_empty_when_no_index_yet(client):
    res = client.get("/api/notes", params={"project_id": "p1"})

    assert res.status_code == 200
    assert res.json() == []


def test_list_notes_groups_chunks_by_source(client):
    index_dir = projects.index_dir("p1")
    index_dir.mkdir(parents=True)
    metadata = [
        {"source": "a.md", "chunk_index": 0, "text": "x"},
        {"source": "a.md", "chunk_index": 1, "text": "y"},
        {"source": "b.txt", "chunk_index": 0, "text": "z"},
    ]
    (index_dir / "metadata.json").write_text(json.dumps(metadata))

    res = client.get("/api/notes", params={"project_id": "p1"})

    assert res.status_code == 200
    assert res.json() == [{"source": "a.md", "chunks": 2}, {"source": "b.txt", "chunks": 1}]


def test_list_notes_are_isolated_per_project(client):
    index_dir = projects.index_dir("p1")
    index_dir.mkdir(parents=True)
    (index_dir / "metadata.json").write_text(
        json.dumps([{"source": "a.md", "chunk_index": 0, "text": "x"}])
    )

    res = client.get("/api/notes", params={"project_id": "p2"})

    assert res.json() == []


def test_upload_notes_rejects_unsupported_extension(client):
    res = client.post(
        "/api/notes",
        data={"project_id": "p1"},
        files=[("files", ("image.png", b"binary", "image/png"))],
    )

    assert res.status_code == 400
    assert "image.png" in res.json()["detail"]


def test_upload_notes_saves_files_and_rebuilds_index(client, monkeypatch, fake_openai_factory):
    from src import ingest

    fake_client = fake_openai_factory(vectors_by_text={"hello world": [1.0, 0.0]})
    monkeypatch.setattr(ingest, "get_client", lambda: fake_client)

    res = client.post(
        "/api/notes",
        data={"project_id": "p1"},
        files=[("files", ("note.txt", b"hello world", "text/plain"))],
    )

    assert res.status_code == 200
    assert res.json() == [{"source": "note.txt", "chunks": 1}]
    assert (projects.notes_dir("p1") / "note.txt").read_text() == "hello world"
    assert (projects.index_dir("p1") / "notes.index").exists()
