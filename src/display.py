"""Turn a stored conversation into what the chat screen shows.

The stored history keeps every tool call and result so the model has full context.
The screen only needs the user/assistant text, plus two things pulled out of the
tool results of that turn: which notes the answer was based on, and any quiz card.
"""

import json

SNIPPET_CHARS = 160
MAX_SOURCES = 3


def find_quiz(messages: list[dict], quiz_id: str) -> dict | None:
    for m in messages:
        if m.get("role") != "tool":
            continue
        payload = _load(m.get("content"))
        if isinstance(payload, dict) and payload.get("quiz_id") == quiz_id:
            return payload
    return None


def public_quiz(quiz: dict, answer: dict | None) -> dict:
    """The quiz as the screen sees it: the answer stays hidden until a choice is made."""
    card = {
        "id": quiz["quiz_id"],
        "topic": quiz.get("topic", ""),
        "question": quiz["question"],
        "choices": quiz["choices"],
        "answered": None,
    }
    if answer is not None:
        card["answered"] = {
            "choice": answer["choice"],
            "correct": answer["correct"],
            "answer_index": quiz["answer_index"],
            "explanation": quiz.get("explanation", ""),
        }
    return card


def quiz_ids(messages: list[dict]) -> list[str]:
    ids = []
    for m in messages:
        if m.get("role") == "tool":
            payload = _load(m.get("content"))
            if isinstance(payload, dict) and payload.get("quiz_id"):
                ids.append(payload["quiz_id"])
    return ids


def visible_messages(messages: list[dict], answers: dict[str, dict]) -> list[dict]:
    tool_names: dict[str, str] = {}
    sources: list[dict] = []
    quizzes: list[dict] = []
    visible = []

    for m in messages:
        role = m.get("role")
        if role == "user":
            sources, quizzes = [], []
            if m.get("content"):
                visible.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            for call in m.get("tool_calls") or []:
                tool_names[call["id"]] = call["function"]["name"]
            if m.get("content"):
                item = {"role": "assistant", "content": m["content"]}
                if sources:
                    item["sources"] = _dedupe(sources)
                if quizzes:
                    item["quiz"] = public_quiz(quizzes[-1], answers.get(quizzes[-1]["quiz_id"]))
                visible.append(item)
                sources, quizzes = [], []
        elif role == "tool":
            name = tool_names.get(m.get("tool_call_id"))
            payload = _load(m.get("content"))
            if name == "search_notes" and isinstance(payload, list):
                sources.extend(p for p in payload if isinstance(p, dict) and p.get("text"))
            elif name == "generate_quiz" and isinstance(payload, dict) and payload.get("quiz_id"):
                quizzes.append(payload)
    return visible


def _dedupe(results: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for r in sorted(results, key=lambda r: -r.get("score", 0)):
        best.setdefault(r.get("source", "노트"), r)
    return [
        {"source": source, "snippet": _snippet(r["text"])}
        for source, r in list(best.items())[:MAX_SOURCES]
    ]


def _snippet(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= SNIPPET_CHARS else flat[:SNIPPET_CHARS].rstrip() + "…"


def _load(content):
    try:
        return json.loads(content) if isinstance(content, str) else None
    except json.JSONDecodeError:
        return None
