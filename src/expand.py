"""Turn a question that describes a concept into the textbook terms it may be about.

People often ask with a description ("한 주기가 끝난 뒤 협업 습관을 되짚는 모임") instead of the
term the notes use ("스프린트 회고"). Embeddings and keyword matching both need a shared word,
so a small model proposes candidate terms and they are added to the search text.
"""

import json

from src.config import settings
from src.ingest import get_client

PROMPT = """학습 노트에서 찾으려는 질문입니다. 질문이 용어를 직접 쓰지 않고 상황, 비유, 일상적인 말로 묘사하고 있을 수 있습니다.
질문이 가리키는 교과서 용어 후보를 3~5개 적으세요. 가장 가능성 높은 것부터, 영어 약어가 흔하면 함께 적으세요.
JSON으로만 답하세요: {{"terms": ["용어1", "용어2"]}}

질문: {question}"""  # noqa: E501 (prompt text)


def expand_query(question: str) -> list[str]:
    """Candidate terms for the question; an empty list on any error, so search just goes without them."""
    try:
        response = get_client().chat.completions.create(
            model=settings.expand_model,
            messages=[{"role": "user", "content": PROMPT.format(question=question)}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        terms = json.loads(response.choices[0].message.content).get("terms", [])
        return [t.strip() for t in terms if isinstance(t, str) and t.strip()][:5]
    except Exception:
        return []
