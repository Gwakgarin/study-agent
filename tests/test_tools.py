import json

from src import tools


def test_search_notes_delegates_to_search_module(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tools, "_search_notes", lambda project_id, query, k: calls.append((project_id, query, k)) or [{"text": "x"}]
    )

    result = tools.search_notes("p1", "faiss란", k=3)

    assert calls == [("p1", "faiss란", 3)]
    assert result == [{"text": "x"}]


def test_generate_quiz_returns_error_when_no_notes_found(monkeypatch):
    monkeypatch.setattr(tools, "_search_notes", lambda project_id, topic, k: [])

    result = tools.generate_quiz("p1", "확산 모델")

    assert "error" in result
    assert "확산 모델" in result["error"]


def test_generate_quiz_builds_prompt_from_retrieved_chunks_and_parses_json(monkeypatch, fake_openai_factory):
    monkeypatch.setattr(
        tools, "_search_notes", lambda project_id, topic, k: [{"text": "FAISS는 벡터 검색 라이브러리"}]
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

    result = tools.generate_quiz("p1", "FAISS", difficulty="easy")

    assert result == quiz
    call_kwargs = fake_client.chat.completions.calls[0]
    assert "FAISS는 벡터 검색 라이브러리" in call_kwargs["messages"][0]["content"]
    assert "easy" in call_kwargs["messages"][0]["content"]


def test_record_answer_delegates_and_echoes_input(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tools, "_record_answer", lambda project_id, topic, correct: calls.append((project_id, topic, correct))
    )

    result = tools.record_answer("p1", "faiss", True)

    assert calls == [("p1", "faiss", True)]
    assert result == {"recorded": True, "topic": "faiss", "correct": True}


def test_get_weak_topics_delegates(monkeypatch):
    monkeypatch.setattr(tools, "_get_weak_topics", lambda project_id: [{"topic": "faiss", "project": project_id}])

    assert tools.get_weak_topics("p1") == [{"topic": "faiss", "project": "p1"}]


def test_tool_schemas_and_build_tool_functions_stay_in_sync():
    schema_names = {schema["function"]["name"] for schema in tools.TOOL_SCHEMAS}
    assert schema_names == set(tools.build_tool_functions("p1").keys())


def test_build_tool_functions_binds_project_id_so_the_model_never_supplies_it(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tools, "_get_weak_topics", lambda project_id: calls.append(project_id) or []
    )

    bound = tools.build_tool_functions("p1")
    bound["get_weak_topics"]()

    assert calls == ["p1"]
