"""Ask a small model whether retrieved notes can answer a query at all.

Similarity scores cannot tell "close wording" from "contains the answer": off-topic
questions score as high as real ones, so this is decided by reading the text instead.
"""

import json

from src.config import settings
from src.ingest import get_client

# The model first names the concept the question points at, then checks the chunks for it.
# Without that step it turned away questions that describe a concept instead of naming it
# ("영상 통화처럼 몇 조각 잃어도 되는 전달 규약" → UDP); on eval/holdout/gate_dev.jsonl that
# went from 7/12 to 10/12 passed while every off-note question was still blocked.
PROMPT = """학습 노트에서 검색한 조각들이 질문에 답하는 데 쓸 수 있는지 판단하세요.

1. 먼저 질문이 묻는 개념이 무엇인지 한 단어나 짧은 이름으로 적으세요. 질문은 용어를 직접 쓰지 않고 상황, 비유, 일상적인 말로 묘사할 수 있습니다.
2. 그 개념의 정의나 설명이 조각 안에 있으면 true. 질문과 조각의 용어가 달라도(예: 별칭과 접두사) 같은 대상을 말하면 같은 내용으로 보고, 일부만 있어도 true.
3. 조각에 그 개념이 없고 비슷한 분야의 다른 개념만 있으면 false. 조각에 없는 개념을 일반 지식으로 채워야 답할 수 있다면 false입니다.
JSON으로만 답하세요: {{"concept": "개념 이름", "answerable": true}} 또는 {{"concept": "개념 이름", "answerable": false}}

{ask}

조각:
{context}"""  # noqa: E501 (prompt text)


def can_answer(query: str, chunks: list[dict], question: str | None = None) -> bool:
    """True when the chunks hold what the query asks for. Fails open: on any error the search results are kept."""
    if not chunks:
        return False
    # A search query is often just keywords; the user's own wording says what is actually asked.
    ask = f"질문: {question}\n검색어: {query}" if question and question != query else f"질문: {query}"
    context = "\n\n---\n\n".join(c["text"] for c in chunks)
    try:
        response = get_client().chat.completions.create(
            model=settings.gate_model,
            messages=[{"role": "user", "content": PROMPT.format(ask=ask, context=context)}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return bool(json.loads(response.choices[0].message.content).get("answerable", True))
    except Exception:
        return True
