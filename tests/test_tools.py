import json

import pytest

from src import tools


@pytest.fixture(autouse=True)
def _no_expansion_calls(monkeypatch):
    # Expansion would call the model; tests that want it turn it on with their own stub.
    monkeypatch.setattr(tools, "expand_query", lambda question: [])


def test_search_notes_delegates_to_search_module(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tools, "_search_notes", lambda project_id, query, k: calls.append((project_id, query, k)) or [{"text": "x"}]
    )

    monkeypatch.setattr(tools, "can_answer", lambda query, chunks, question=None: True)

    result = tools.search_notes("p1", "faiss란", k=3)

    assert calls == [("p1", "faiss란", 3)]
    assert result == [{"text": "x"}]


def test_search_notes_returns_nothing_when_gate_says_no(monkeypatch):
    monkeypatch.setattr(tools, "_search_notes", lambda project_id, query, k: [{"text": "x"}])
    monkeypatch.setattr(tools, "can_answer", lambda query, chunks, question=None: False)

    assert tools.search_notes("p1", "트리거란") == []


def test_search_notes_retries_with_the_users_question_when_the_query_misses(monkeypatch):
    searched = []

    def fake_search(project_id, query, k):
        searched.append(query)
        return [{"text": query}]

    monkeypatch.setattr(tools, "_search_notes", fake_search)
    monkeypatch.setattr(
        tools, "can_answer", lambda query, chunks, question=None: query == "NULL이 뭐야?" and question is None
    )

    assert tools.search_notes("p1", "빈 문자열", _question="NULL이 뭐야?") == [{"text": "NULL이 뭐야?"}]
    assert searched == ["빈 문자열", "NULL이 뭐야?"]


def test_search_notes_searches_again_with_expanded_terms_when_the_gate_says_no(monkeypatch):
    searched = []

    def fake_search(project_id, query, k):
        searched.append(query)
        return [{"text": "회고" if "스프린트 회고" in query else "x"}]

    monkeypatch.setattr(tools, "_search_notes", fake_search)
    monkeypatch.setattr(tools, "expand_query", lambda question: ["스프린트 회고", "KPT"])
    monkeypatch.setattr(tools, "can_answer", lambda query, chunks, question=None: chunks[0]["text"] == "회고")

    results = tools.search_notes("p1", "키워드", _question="한 주기 끝나고 되짚는 모임은?")

    assert results == [{"text": "회고"}]
    assert searched[-1] == "한 주기 끝나고 되짚는 모임은? 스프린트 회고 KPT"


def test_search_notes_stays_empty_when_expanded_search_still_fails_the_gate(monkeypatch):
    monkeypatch.setattr(tools, "_search_notes", lambda project_id, query, k: [{"text": "x"}])
    monkeypatch.setattr(tools, "expand_query", lambda question: ["용어"])
    monkeypatch.setattr(tools, "can_answer", lambda query, chunks, question=None: False)

    assert tools.search_notes("p1", "트리거란") == []


def test_search_notes_does_not_expand_when_turned_off(monkeypatch):
    def boom(question):
        raise AssertionError("expand_query should not run")

    monkeypatch.setattr(tools, "_search_notes", lambda project_id, query, k: [{"text": "x"}])
    monkeypatch.setattr(tools, "expand_query", boom)
    monkeypatch.setattr(tools, "can_answer", lambda query, chunks, question=None: False)
    monkeypatch.setattr(tools.settings, "query_expansion", False)

    assert tools.search_notes("p1", "트리거란") == []


def test_search_notes_skips_gate_when_disabled(monkeypatch):
    monkeypatch.setattr(tools, "_search_notes", lambda project_id, query, k: [{"text": "x"}])
    monkeypatch.setattr(tools, "can_answer", lambda query, chunks, question=None: False)
    monkeypatch.setattr(tools.settings, "answer_gate", False)

    assert tools.search_notes("p1", "트리거란") == [{"text": "x"}]


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

    assert {k: result[k] for k in quiz} == quiz
    assert result["topic"] == "FAISS"
    assert len(result["quiz_id"]) == 32
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


def test_generate_quiz_rejects_malformed_quiz(monkeypatch, fake_openai_factory):
    monkeypatch.setattr(tools, "_search_notes", lambda project_id, topic, k: [{"text": "x"}])
    bad = {"question": "Q", "choices": ["a", "b"], "answer_index": 5, "explanation": ""}
    fake_client = fake_openai_factory()
    fake_client.chat.completions._responses = [
        type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": json.dumps(bad)})()})()]})()
    ]
    monkeypatch.setattr(tools, "get_client", lambda: fake_client)

    assert "error" in tools.generate_quiz("p1", "x")
