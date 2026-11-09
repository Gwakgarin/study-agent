"""Ask a small model whether retrieved notes can answer a query at all.

Similarity scores cannot tell "close wording" from "contains the answer": off-topic
questions score as high as real ones, so this is decided by reading the text instead.
"""

import json

from src.config import settings
from src.ingest import get_client

PROMPT = """학습 노트에서 검색한 조각들이 질문에 답하는 데 쓸 수 있는지 판단하세요.

- 답의 핵심 내용이 조각 안에 있으면 true. 질문과 조각의 용어가 달라도(예: 별칭과 접두사) 같은 대상을 말하면 같은 내용으로 보고, 일부만 있어도 true.
- 같은 분야의 단어만 겹치고 질문이 묻는 내용 자체는 없으면 false.
JSON으로만 답하세요: {{"answerable": true}} 또는 {{"answerable": false}}

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
