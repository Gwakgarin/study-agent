import json

from src import tools


def test_search_notes_delegates_to_search_module(monkeypatch):
    calls = []
    monkeypatch.setattr(tools, "_search_notes", lambda query, k: calls.append((query, k)) or [{"text": "x"}])

    result = tools.search_notes("faiss란", k=3)

    assert calls == [("faiss란", 3)]
    assert result == [{"text": "x"}]


def test_generate_quiz_returns_error_when_no_notes_found(monkeypatch):
    monkeypatch.setattr(tools, "_search_notes", lambda topic, k: [])

    result = tools.generate_quiz("확산 모델")

    assert "error" in result
    assert "확산 모델" in result["error"]


def test_generate_quiz_builds_prompt_from_retrieved_chunks_and_parses_json(monkeypatch, fake_openai_factory):
    monkeypatch.setattr(
        tools, "_search_notes", lambda topic, k: [{"text": "FAISS는 벡터 검색 라이브러리"}]
    )
    quiz = {
        "question": "FAISS는 무엇인가?",
        "choices": ["DB", "벡터 검색 라이브러리", "OS", "언어"],
        "answer_index": 1,
        "explanation": "...",
    }
    fake_client = fake_openai_factory()
    fake_client.chat.completions._responses = [
        type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": json.dumps(quiz)})()})()]})()
    ]
    monkeypatch.setattr(tools, "get_client", lambda: fake_client)

    result = tools.generate_quiz("FAISS", difficulty="easy")

    assert result == quiz
    call_kwargs = fake_client.chat.completions.calls[0]
    assert "FAISS는 벡터 검색 라이브러리" in call_kwargs["messages"][0]["content"]
    assert "easy" in call_kwargs["messages"][0]["content"]


def test_record_answer_delegates_and_echoes_input(monkeypatch):
    calls = []
    monkeypatch.setattr(tools, "_record_answer", lambda topic, correct: calls.append((topic, correct)))

    result = tools.record_answer("faiss", True)

    assert calls == [("faiss", True)]
    assert result == {"recorded": True, "topic": "faiss", "correct": True}


def test_get_weak_topics_delegates(monkeypatch):
    monkeypatch.setattr(tools, "_get_weak_topics", lambda: [{"topic": "faiss"}])

    assert tools.get_weak_topics() == [{"topic": "faiss"}]


def test_tool_schemas_and_functions_stay_in_sync():
    schema_names = {schema["function"]["name"] for schema in tools.TOOL_SCHEMAS}
    assert schema_names == set(tools.TOOL_FUNCTIONS.keys())
