import json

import pytest
from fastapi.testclient import TestClient

import server
from src import auth, projects, sessions, usage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "study-agent.db"
    for module in (sessions, projects, auth, usage):
        monkeypatch.setattr(module, "DB_PATH", db_path)
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")


@pytest.fixture
def client():
    """A client already signed up and logged in as one user."""
    c = TestClient(server.app)
    assert c.post("/api/auth/signup", json={"username": "alice", "password": "password1"}).status_code == 200
    return c


@pytest.fixture
def p1(client):
    return client.post("/api/projects", json={"name": "과목1"}).json()["id"]


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


def test_create_session_returns_id_and_empty_messages(client, p1):
    res = client.post("/api/session", json={"project_id": p1})

    assert res.status_code == 200
    data = res.json()
    assert data["session_id"]
    assert data["messages"] == []


def test_create_session_injects_due_topics_greeting(client, p1, monkeypatch):
    monkeypatch.setattr(
        server, "get_due_topics", lambda project_id: [{"topic": "faiss", "next_review_at": "..."}]
    )

    res = client.post("/api/session", json={"project_id": p1})

    messages = res.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert "faiss" in messages[0]["content"]


def test_chat_appends_user_and_assistant_messages(client, p1, monkeypatch):
    _stub_run_turn(monkeypatch, reply="안녕!")

    session_id = client.post("/api/session", json={"project_id": p1}).json()["session_id"]
    res = client.post("/api/chat", json={"session_id": session_id, "project_id": p1, "message": "hi"})

    assert res.status_code == 200
    messages = res.json()["messages"]
    assert messages[-2] == {"role": "user", "content": "hi"}
    assert messages[-1] == {"role": "assistant", "content": "안녕!"}


def test_chat_history_persists_across_separate_requests(client, p1, monkeypatch):
    """Regression test: history used to live only in an in-memory dict, lost on restart."""
    replies = iter(["first reply", "second reply"])

    def fake_run_turn(messages, project_id):
        messages.append({"role": "assistant", "content": next(replies)})
        return messages

    monkeypatch.setattr(server, "run_turn", fake_run_turn)

    session_id = client.post("/api/session", json={"project_id": p1}).json()["session_id"]
    client.post("/api/chat", json={"session_id": session_id, "project_id": p1, "message": "first"})
    res = client.post("/api/chat", json={"session_id": session_id, "project_id": p1, "message": "second"})

    contents = [m["content"] for m in res.json()["messages"]]
    assert contents == ["first", "first reply", "second", "second reply"]

    # and it's actually durable, not just held in a local variable
    assert sessions.load_session(session_id) is not None


def test_chat_with_unknown_session_id_starts_a_fresh_conversation(client, p1, monkeypatch):
    _stub_run_turn(monkeypatch, reply="hi there")

    res = client.post(
        "/api/chat", json={"session_id": "never-created", "project_id": p1, "message": "hello"}
    )

    assert res.status_code == 200
    assert res.json()["messages"][0] == {"role": "user", "content": "hello"}


def test_reset_clears_session_history(client, p1, monkeypatch):
    _stub_run_turn(monkeypatch)

    session_id = client.post("/api/session", json={"project_id": p1}).json()["session_id"]
    client.post("/api/chat", json={"session_id": session_id, "project_id": p1, "message": "hi"})

    res = client.post("/api/reset", json={"session_id": session_id, "project_id": p1})

    assert res.json()["messages"] == []
    assert sessions.load_session(session_id) == server.new_conversation()


def test_weak_topics_endpoint_returns_tracker_data(client, p1, monkeypatch):
    monkeypatch.setattr(
        server, "get_weak_topics", lambda project_id: [{"topic": "faiss", "wrong_rate": 0.5}]
    )

    res = client.get("/api/weak-topics", params={"project_id": p1})

    assert res.status_code == 200
    assert res.json() == [{"topic": "faiss", "wrong_rate": 0.5}]


def test_weak_topics_endpoint_returns_500_on_error(client, p1, monkeypatch):
    def boom(project_id):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(server, "get_weak_topics", boom)

    res = client.get("/api/weak-topics", params={"project_id": p1})

    assert res.status_code == 500


def test_list_notes_returns_empty_when_no_index_yet(client, p1):
    res = client.get("/api/notes", params={"project_id": p1})

    assert res.status_code == 200
    assert res.json() == []


def test_list_notes_groups_chunks_by_source(client, p1):
    index_dir = projects.index_dir(p1)
    index_dir.mkdir(parents=True)
    metadata = [
        {"source": "a.md", "chunk_index": 0, "text": "x"},
        {"source": "a.md", "chunk_index": 1, "text": "y"},
        {"source": "b.txt", "chunk_index": 0, "text": "z"},
    ]
    (index_dir / "metadata.json").write_text(json.dumps(metadata))

    res = client.get("/api/notes", params={"project_id": p1})

    assert res.status_code == 200
    assert res.json() == [{"source": "a.md", "chunks": 2}, {"source": "b.txt", "chunks": 1}]


def test_list_notes_are_isolated_per_project(client, p1):
    index_dir = projects.index_dir(p1)
    index_dir.mkdir(parents=True)
    (index_dir / "metadata.json").write_text(
        json.dumps([{"source": "a.md", "chunk_index": 0, "text": "x"}])
    )

    p2 = client.post("/api/projects", json={"name": "과목2"}).json()["id"]
    res = client.get("/api/notes", params={"project_id": p2})

    assert res.json() == []


def test_upload_notes_rejects_unsupported_extension(client, p1):
    res = client.post(
        "/api/notes",
        data={"project_id": p1},
        files=[("files", ("image.png", b"binary", "image/png"))],
    )

    assert res.status_code == 400
    assert "image.png" in res.json()["detail"]


def test_upload_notes_saves_files_and_rebuilds_index(client, p1, monkeypatch, fake_openai_factory):
    from src import ingest

    fake_client = fake_openai_factory(vectors_by_text={"hello world": [1.0, 0.0]})
    monkeypatch.setattr(ingest, "get_client", lambda: fake_client)

    res = client.post(
        "/api/notes",
        data={"project_id": p1},
        files=[("files", ("note.txt", b"hello world", "text/plain"))],
    )

    assert res.status_code == 200
    assert res.json() == [{"source": "note.txt", "chunks": 1}]
    assert (projects.notes_dir(p1) / "note.txt").read_text() == "hello world"
    assert (projects.index_dir(p1) / "notes.index").exists()


def _openai_error(kind):
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    if kind == "timeout":
        return openai.APITimeoutError(request=request)
    if kind == "connection":
        return openai.APIConnectionError(request=request)
    status = {"rate_limit": 429, "auth": 401, "server": 500}[kind]
    cls = {
        "rate_limit": openai.RateLimitError,
        "auth": openai.AuthenticationError,
        "server": openai.InternalServerError,
    }[kind]
    return cls("error", response=httpx.Response(status, request=request), body=None)


@pytest.mark.parametrize(
    "kind, expected_status",
    [("timeout", 504), ("rate_limit", 429), ("connection", 503), ("auth", 500), ("server", 502)],
)
def test_chat_maps_openai_failures_to_clear_errors(client, p1, monkeypatch, kind, expected_status):
    def failing_run_turn(messages, project_id):
        raise _openai_error(kind)

    monkeypatch.setattr(server, "run_turn", failing_run_turn)
    session_id = client.post("/api/session", json={"project_id": p1}).json()["session_id"]

    res = client.post("/api/chat", json={"session_id": session_id, "project_id": p1, "message": "hi"})

    assert res.status_code == expected_status
    assert res.json()["detail"]


def test_failed_chat_leaves_saved_session_unchanged(client, p1, monkeypatch):
    _stub_run_turn(monkeypatch, reply="first reply")
    session_id = client.post("/api/session", json={"project_id": p1}).json()["session_id"]
    client.post("/api/chat", json={"session_id": session_id, "project_id": p1, "message": "first"})
    before = sessions.load_session(session_id)

    def failing_run_turn(messages, project_id):
        raise _openai_error("timeout")

    monkeypatch.setattr(server, "run_turn", failing_run_turn)
    res = client.post("/api/chat", json={"session_id": session_id, "project_id": p1, "message": "second"})

    assert res.status_code == 504
    assert sessions.load_session(session_id) == before


def test_chat_returns_502_when_tool_loop_never_finishes(client, p1, monkeypatch):
    def looping_run_turn(messages, project_id):
        raise server.ToolLoopError("no final answer")

    monkeypatch.setattr(server, "run_turn", looping_run_turn)

    res = client.post("/api/chat", json={"session_id": "s1", "project_id": p1, "message": "hi"})

    assert res.status_code == 502


def _basic(password, user="me"):
    import base64

    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


def test_health_is_open_even_with_password(client, monkeypatch):
    monkeypatch.setattr(server.settings, "access_password", "s3cret")

    res = client.get("/api/health")

    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_password_required_when_configured(client, monkeypatch):
    monkeypatch.setattr(server.settings, "access_password", "s3cret")

    res = client.get("/api/projects")

    assert res.status_code == 401
    assert res.headers["www-authenticate"].startswith("Basic")


def test_wrong_password_is_rejected(client, monkeypatch):
    monkeypatch.setattr(server.settings, "access_password", "s3cret")

    assert client.get("/api/projects", headers=_basic("nope")).status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Basic !!!"}).status_code == 401


def test_correct_password_with_any_username_passes(client, monkeypatch):
    monkeypatch.setattr(server.settings, "access_password", "s3cret")

    res = client.get("/api/projects", headers=_basic("s3cret", user="anyone"))

    assert res.status_code == 200


def test_no_password_configured_leaves_api_open(client, monkeypatch):
    monkeypatch.setattr(server.settings, "access_password", None)

    assert client.get("/api/projects").status_code == 200
