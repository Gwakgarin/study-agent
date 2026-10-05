import json

import pytest
from fastapi.testclient import TestClient

import server
from src import agent, auth, projects, quizzes, sessions, tracker, usage
from tests.conftest import FakeOpenAI, make_stream


def _run(messages, fake_client, tools, monkeypatch):
    monkeypatch.setattr(agent, "get_client", lambda: fake_client)
    monkeypatch.setattr(agent, "build_tool_functions", lambda project_id: tools)
    return list(agent.run_turn_stream(messages, "p1"))


def test_streams_text_and_saves_final_message(monkeypatch):
    fake = FakeOpenAI(chat_responses=[make_stream(["안녕", "하세요"])])
    messages = agent.new_conversation() + [{"role": "user", "content": "hi"}]

    events = _run(messages, fake, {}, monkeypatch)

    assert events == [("delta", "안녕"), ("delta", "하세요")]
    assert messages[-1] == {"role": "assistant", "content": "안녕하세요"}
    assert fake.chat.completions.calls[0]["stream"] is True


def test_reassembles_split_tool_call_then_streams_answer(monkeypatch):
    fake = FakeOpenAI(
        chat_responses=[
            make_stream(tool_calls=[(0, "call_1", "search_notes", ['{"que', 'ry": "조인"}'])]),
            make_stream(["조인은", " ..."]),
        ]
    )
    seen = []
    tools = {"search_notes": lambda query: seen.append(query) or [{"text": "조인 설명"}]}
    messages = agent.new_conversation() + [{"role": "user", "content": "조인?"}]

    events = _run(messages, fake, tools, monkeypatch)

    assert seen == ["조인"]
    assert events[0] == ("status", "노트를 찾고 있어요")
    assert [t for k, t in events if k == "delta"] == ["조인은", " ..."]
    call = messages[-3]["tool_calls"][0]
    assert call["function"] == {"name": "search_notes", "arguments": '{"query": "조인"}'}
    assert json.loads(messages[-2]["content"]) == [{"text": "조인 설명"}]
    assert messages[-1]["content"] == "조인은 ..."


def test_stream_stops_runaway_tool_loop(monkeypatch):
    monkeypatch.setattr(agent.settings, "max_tool_rounds", 2)
    fake = FakeOpenAI(
        chat_responses=[make_stream(tool_calls=[(0, f"c{i}", "search_notes", ["{}"])]) for i in range(3)]
    )

    with pytest.raises(agent.ToolLoopError):
        _run(agent.new_conversation(), fake, {"search_notes": lambda: []}, monkeypatch)


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "study-agent.db"
    for module in (sessions, projects, auth, usage, quizzes, tracker):
        monkeypatch.setattr(module, "DB_PATH", db_path)
    monkeypatch.setattr(projects, "PROJECTS_ROOT", tmp_path / "projects")
    c = TestClient(server.app)
    c.post("/api/auth/signup", json={"username": "alice", "password": "password1"})
    return c


def _events(res):
    return [json.loads(line[6:]) for line in res.text.splitlines() if line.startswith("data: ")]


def _body(client):
    project_id = client.post("/api/projects", json={"name": "A"}).json()["id"]
    session_id = client.post("/api/session", json={"project_id": project_id}).json()["session_id"]
    return {"session_id": session_id, "project_id": project_id, "message": "hi"}


def test_stream_endpoint_sends_events_and_saves_session(client, monkeypatch):
    def fake_stream(messages, project_id):
        yield "status", "노트를 찾고 있어요"
        yield "delta", "답"
        messages.append({"role": "assistant", "content": "답"})

    monkeypatch.setattr(server, "run_turn_stream", fake_stream)
    body = _body(client)

    res = client.post("/api/chat/stream", json=body)

    events = _events(res)
    assert res.headers["content-type"].startswith("text/event-stream")
    assert [e["type"] for e in events] == ["status", "delta", "done"]
    assert events[-1]["messages"][-1] == {"role": "assistant", "content": "답"}
    assert sessions.load_session(body["session_id"])[-1]["content"] == "답"


def test_stream_error_is_an_event_and_nothing_is_saved(client, monkeypatch):
    def failing(messages, project_id):
        yield "delta", "반쯤"
        raise server.ToolLoopError("loop")

    monkeypatch.setattr(server, "run_turn_stream", failing)
    body = _body(client)
    before = sessions.load_session(body["session_id"])

    events = _events(client.post("/api/chat/stream", json=body))

    assert events[-1] == {"type": "error", "status": 502, "detail": events[-1]["detail"]}
    assert sessions.load_session(body["session_id"]) == before


def test_stream_checks_happen_before_streaming(client, monkeypatch):
    monkeypatch.setattr(server.settings, "chat_limit_per_hour", 0)
    body = _body(client)

    res = client.post("/api/chat/stream", json=body)

    assert res.status_code == 429
