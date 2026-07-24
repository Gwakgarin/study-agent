"""Tool-calling conversation loop for the study agent."""

import json

from src.config import settings
from src.ingest import get_client
from src.tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

CHAT_MODEL = settings.chat_model

SYSTEM_PROMPT = (
    "당신은 사용자의 공부를 도와주는 학습 에이전트입니다. "
    "질문에 답하기 전에는 반드시 search_notes로 노트를 먼저 검색하세요. "
    "노트에 없는 내용은 모른다고 솔직히 말하세요. "
    "사용자가 퀴즈를 요청하면 get_weak_topics로 약점 주제를 확인하고, "
    "약점 주제가 있으면 그 중 하나를 우선 출제하세요. "
    "사용자가 퀴즈에 답하면 record_answer로 정답 여부를 기록하세요."
)


def new_conversation() -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def run_turn(messages: list[dict]) -> list[dict]:
    """Run one assistant turn, including any tool calls, appending to messages."""
    client = get_client()

    while True:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return messages

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            func = TOOL_FUNCTIONS.get(name)
            result = func(**args) if func else {"error": f"Unknown tool: {name}"}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
