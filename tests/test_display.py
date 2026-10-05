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
                    {"source": "b.md", "text": "다른 노트", "score": 0.7},
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
