"""Turn a stored conversation into what the chat screen shows.

The stored history keeps every tool call and result so the model has full context.
The screen only needs the user/assistant text, plus two things pulled out of the
tool results of that turn: which notes the answer was based on, and any quiz card.
"""

import json
import re

SNIPPET_CHARS = 160
MAX_SOURCES = 3
# Notes scoring this far below the best match are left off the list; showing a
# barely related file as a "source" makes the answer look less trustworthy.
SOURCE_SCORE_MARGIN = 0.1
# A written answer lists a note only if at least this share of the answer's character
# pairs appear in it. On the eval answers this kept the evidence chunk for 107 of 108
# correct answers and left 39 of 40 off-note answers with no source.
MIN_ANSWER_OVERLAP = 0.4


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
                # A quiz reply is a one-line pointer to the card, so there is no answer
                # text to check the notes against.
                shown = _dedupe(sources, None if quizzes else m["content"])
                if shown:
                    item["sources"] = shown
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


def _dedupe(results: list[dict], answer: str | None = None) -> list[dict]:
    ranked = sorted(results, key=lambda r: -r.get("score", 0))
    if answer is None:
        top = ranked[0].get("score", 0) if ranked else 0
        ranked = [r for r in ranked if r.get("score", 0) >= top - SOURCE_SCORE_MARGIN]
    else:
        # Search returns its nearest chunks even when none is about the question, and a
        # reworded query can score an unrelated chunk higher than real evidence. Whether
        # the answer actually repeats a chunk's wording separates the two far better.
        ranked = [r for r in ranked if _overlap(answer, r["text"]) >= MIN_ANSWER_OVERLAP]
    best: dict[str, dict] = {}
    for r in ranked:
        best.setdefault(r.get("source", "노트"), r)
    return [
        {"source": source, "snippet": _snippet(r["text"])}
        for source, r in list(best.items())[:MAX_SOURCES]
    ]


def _bigrams(text: str) -> set[str]:
    # Character pairs rather than words, so Korean particles (정규화는 / 정규화를) still match.
    flat = "".join(text.lower().split())
    return {flat[i : i + 2] for i in range(len(flat) - 1)}


def _overlap(answer: str, chunk: str) -> float:
    """Share of the answer's character pairs that also appear in the chunk."""
    pairs = _bigrams(answer)
    return len(pairs & _bigrams(chunk)) / len(pairs) if pairs else 0.0


def _snippet(text: str) -> str:
    # Notes are often Markdown; heading marks and emphasis read as noise in a preview.
    plain = re.sub(r"(^|\n)\s*#{1,6}\s*", r"\1", text)
    plain = re.sub(r"[*_`]{1,3}", "", plain)
    flat = " ".join(plain.split())
    return flat if len(flat) <= SNIPPET_CHARS else flat[:SNIPPET_CHARS].rstrip() + "…"


def _load(content):
    try:
        return json.loads(content) if isinstance(content, str) else None
    except json.JSONDecodeError:
        return None
