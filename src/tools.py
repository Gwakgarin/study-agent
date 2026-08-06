"""Tool definitions (OpenAI function-calling schemas + implementations) for the study agent."""

import functools
import json

from src.config import settings
from src.ingest import get_client
from src.search import search_notes as _search_notes
from src.tracker import get_weak_topics as _get_weak_topics
from src.tracker import record_answer as _record_answer

QUIZ_MODEL = settings.quiz_model


def search_notes(project_id: str, query: str, k: int = 5) -> list[dict]:
    return _search_notes(project_id, query, k=k)


def generate_quiz(project_id: str, topic: str, difficulty: str = "medium") -> dict:
    chunks = _search_notes(project_id, topic, k=3)
    if not chunks:
        return {"error": f"'{topic}'에 대한 노트를 찾지 못했습니다. 먼저 관련 노트를 색인했는지 확인하세요."}

    context = "\n\n".join(chunk["text"] for chunk in chunks)
    prompt = (
        f"다음 노트 내용을 바탕으로 '{topic}'에 대한 {difficulty} 난이도의 "
        "객관식 문제를 하나 만들어주세요.\n\n"
        f"노트 내용:\n{context}\n\n"
        '아래 JSON 형식으로만 답하세요: '
        '{"question": "...", "choices": ["...", "...", "...", "..."], '
        '"answer_index": 0, "explanation": "..."}'
    )

    response = get_client().chat.completions.create(
        model=QUIZ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def record_answer(project_id: str, topic: str, correct: bool) -> dict:
    _record_answer(project_id, topic, correct)
    return {"recorded": True, "topic": topic, "correct": correct}


def get_weak_topics(project_id: str) -> list[dict]:
    return _get_weak_topics(project_id)


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "사용자의 공부 노트에서 관련 내용을 검색한다. 질문에 답하기 전에 항상 먼저 호출한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 질문/키워드"},
                    "k": {"type": "integer", "description": "가져올 결과 개수", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_quiz",
            "description": "특정 주제에 대해 노트 내용을 바탕으로 객관식 퀴즈를 하나 생성한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "퀴즈를 낼 주제"},
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"],
                        "default": "medium",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_answer",
            "description": "사용자가 퀴즈에 답한 결과(정답/오답)를 주제별로 기록한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "correct": {"type": "boolean"},
                },
                "required": ["topic", "correct"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weak_topics",
            "description": "오답률이 높은 약점 주제 목록을 조회한다. 다음 퀴즈 주제를 정할 때 사용한다.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def build_tool_functions(project_id: str) -> dict:
    """Bind each tool to a specific project so the model never has to name one itself."""
    return {
        "search_notes": functools.partial(search_notes, project_id),
        "generate_quiz": functools.partial(generate_quiz, project_id),
        "record_answer": functools.partial(record_answer, project_id),
        "get_weak_topics": functools.partial(get_weak_topics, project_id),
    }
