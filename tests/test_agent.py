import json

from src import agent
from tests.conftest import FakeOpenAI, make_message_response, make_tool_call_response


def test_new_conversation_starts_with_system_prompt_only():
    messages = agent.new_conversation()

    assert len(messages) == 1
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == agent.SYSTEM_PROMPT


def test_run_turn_returns_immediately_when_no_tool_calls(monkeypatch):
    fake_client = FakeOpenAI(chat_responses=[make_message_response("안녕하세요")])
    monkeypatch.setattr(agent, "get_client", lambda: fake_client)

    messages = agent.new_conversation()
    messages.append({"role": "user", "content": "hi"})

    result = agent.run_turn(messages)

    assert result[-1] == {"role": "assistant", "content": "안녕하세요"}
    assert len(fake_client.chat.completions.calls) == 1


def test_run_turn_dispatches_tool_call_then_returns_final_message(monkeypatch):
    fake_client = FakeOpenAI(
        chat_responses=[
            make_tool_call_response([("call_1", "search_notes", json.dumps({"query": "faiss"}))]),
            make_message_response("검색 결과를 바탕으로 답할게요"),
        ]
    )
    monkeypatch.setattr(agent, "get_client", lambda: fake_client)

    calls = []
    fake_tools = {"search_notes": lambda query: calls.append(query) or [{"text": "..."}]}
    monkeypatch.setattr(agent, "TOOL_FUNCTIONS", fake_tools)

    messages = agent.new_conversation()
    messages.append({"role": "user", "content": "faiss 설명해줘"})

    result = agent.run_turn(messages)

    assert calls == ["faiss"]
    tool_message = next(m for m in result if m["role"] == "tool")
    assert tool_message["tool_call_id"] == "call_1"
    assert json.loads(tool_message["content"]) == [{"text": "..."}]
    assert result[-1]["content"] == "검색 결과를 바탕으로 답할게요"
    assert len(fake_client.chat.completions.calls) == 2


def test_run_turn_reports_unknown_tool_without_crashing(monkeypatch):
    fake_client = FakeOpenAI(
        chat_responses=[
            make_tool_call_response([("call_1", "not_a_real_tool", "{}")]),
            make_message_response("done"),
        ]
    )
    monkeypatch.setattr(agent, "get_client", lambda: fake_client)
    monkeypatch.setattr(agent, "TOOL_FUNCTIONS", {})

    messages = agent.new_conversation()
    result = agent.run_turn(messages)

    tool_message = next(m for m in result if m["role"] == "tool")
    assert json.loads(tool_message["content"]) == {"error": "Unknown tool: not_a_real_tool"}
