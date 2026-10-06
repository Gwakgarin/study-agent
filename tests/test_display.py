import json

from src import display


def _call(call_id, name):
    return {"id": call_id, "function": {"name": name, "arguments": "{}"}}


QUIZ = {
    "question": "정규화는 어느 단계?",
    "choices": ["개념", "논리", "물리", "운영"],
    "answer_index": 1,
    "explanation": "논리적 모델링",
    "quiz_id": "q1",
    "topic": "정규화",
}


def _turn():
    return [
        {"role": "system", "content": "prompt"},
        {"role": "user", "content": "퀴즈 내줘"},
        {"role": "assistant", "tool_calls": [_call("c1", "search_notes"), _call("c2", "generate_quiz")]},
        {
            "role": "tool",
            "tool_call_id": "c1",
            "content": json.dumps(
                [
                    {"source": "a.md", "text": "정규화는 논리적 모델링 단계", "score": 0.9},
                    {"source": "a.md", "text": "덜 관련된 조각", "score": 0.5},
                    {"source": "b.md", "text": "다른 노트", "score": 0.85},
                ],
                ensure_ascii=False,
            ),
        },
        {"role": "tool", "tool_call_id": "c2", "content": json.dumps(QUIZ, ensure_ascii=False)},
        {"role": "assistant", "content": "정규화 문제를 냈어요."},
    ]


def test_hides_system_and_tool_messages():
    visible = display.visible_messages(_turn(), {})

    assert [m["role"] for m in visible] == ["user", "assistant"]


def test_attaches_best_snippet_per_source_in_score_order():
    answer = display.visible_messages(_turn(), {})[-1]

    assert answer["sources"] == [
        {"source": "a.md", "snippet": "정규화는 논리적 모델링 단계"},
        {"source": "b.md", "snippet": "다른 노트"},
    ]


def test_quiz_card_hides_answer_until_answered():
    card = display.visible_messages(_turn(), {})[-1]["quiz"]

    assert card["question"] == QUIZ["question"]
    assert card["answered"] is None
    assert "answer_index" not in card


def test_quiz_card_shows_result_after_answer():
    card = display.visible_messages(_turn(), {"q1": {"choice": 0, "correct": False}})[-1]["quiz"]

    assert card["answered"] == {"choice": 0, "correct": False, "answer_index": 1, "explanation": "논리적 모델링"}


def test_sources_do_not_leak_into_the_next_turn():
    messages = _turn() + [
        {"role": "user", "content": "고마워"},
        {"role": "assistant", "content": "천만에요"},
    ]

    last = display.visible_messages(messages, {})[-1]

    assert "sources" not in last and "quiz" not in last


def test_long_snippets_are_cut():
    assert display._snippet("가" * 500).endswith("…")
    assert len(display._snippet("가" * 500)) == display.SNIPPET_CHARS + 1


def test_find_quiz_and_quiz_ids():
    messages = _turn()

    assert display.find_quiz(messages, "q1")["answer_index"] == 1
    assert display.find_quiz(messages, "nope") is None
    assert display.quiz_ids(messages) == ["q1"]


def test_snippet_drops_markdown_marks():
    assert display._snippet("# 제목\n## 소제목\n**굵게** 본문 `code`") == "제목 소제목 굵게 본문 code"


def test_weakly_related_notes_are_not_listed_as_sources():
    results = [
        {"source": "a.md", "text": "정답 근거", "score": 0.62},
        {"source": "b.md", "text": "꽤 관련", "score": 0.55},
        {"source": "c.md", "text": "거의 무관", "score": 0.41},
    ]

    assert [s["source"] for s in display._dedupe(results)] == ["a.md", "b.md"]


def _answer_turn(answer, results):
    return [
        {"role": "user", "content": "질문"},
        {"role": "assistant", "tool_calls": [_call("c1", "search_notes")]},
        {"role": "tool", "tool_call_id": "c1", "content": json.dumps(results, ensure_ascii=False)},
        {"role": "assistant", "content": answer},
    ]


def test_written_answer_lists_only_notes_it_draws_on():
    results = [
        {"source": "b.md", "text": "해시 조인은 등가 조인에서만 사용할 수 있다", "score": 0.45},
        {"source": "a.md", "text": "정규화는 논리적 모델링 단계에서 수행한다", "score": 0.41},
    ]

    answer = display.visible_messages(_answer_turn("정규화는 논리적 모델링 단계에서 수행합니다.", results), {})[-1]

    assert [s["source"] for s in answer["sources"]] == ["a.md"]


def test_off_note_answer_gets_no_sources():
    # A reworded search ("트리거 사용") pulls unrelated chunks; a refusal or a
    # general-knowledge answer must not be shown as if those notes backed it.
    results = [
        {"source": "06_관리구문과_튜닝.md", "text": "선행 테이블이 작을수록 유리하다", "score": 0.41},
        {"source": "03_SQL_기본.md", "text": "집계 결과에 대한 조건은 HAVING 절에 작성한다", "score": 0.33},
    ]

    refusal = "노트에서 트리거에 대한 내용을 찾지 못했어요."
    general = "트리거는 INSERT, UPDATE 같은 이벤트에 자동으로 실행됩니다."
    for text in [refusal, general]:
        answer = display.visible_messages(_answer_turn(text, results), {})[-1]
        assert "sources" not in answer
