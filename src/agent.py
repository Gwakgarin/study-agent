"""Tool-calling conversation loop for the study agent."""

import json

from src.config import settings
from src.ingest import get_client
from src.tools import TOOL_SCHEMAS, build_tool_functions

CHAT_MODEL = settings.chat_model

SYSTEM_PROMPT = (
    "당신은 사용자의 공부 노트로만 답하는 학습 에이전트입니다.\n"
    "질문에 답하기 전에는 반드시 search_notes로 노트를 먼저 검색하세요.\n"
    "검색 결과에 질문과 관련된 문장이 하나라도 있으면 그 문장을 근거로 답하세요. "
    "노트의 표현과 사전 지식이 다르면 노트를 따르세요.\n"
    "관련 문장이 없어 보이면 '노트에 없다'고 하기 전에 질문의 핵심 용어나 다른 표현으로 "
    "search_notes를 한 번 더 호출하세요.\n"
    "두 번 검색해도 없을 때만 '노트에서 찾지 못했어요'라고 답하고, 관련 노트를 올리면 "
    "답할 수 있다고 안내하세요. 이때 '다만 일반적으로는'처럼 사전 지식으로 설명을 덧붙이지 마세요.\n"
    "사용자가 퀴즈를 요청하면 get_weak_topics로 약점 주제를 확인하고, "
    "약점 주제가 있으면 그 중 하나를 우선 출제하세요. "
    "generate_quiz로 만든 문제는 화면에 보기 버튼이 있는 카드로 따로 표시되니, "
    "답변에 문제, 보기, 정답을 다시 쓰지 말고 한두 문장으로 무엇을 냈는지만 안내하세요. "
    "사용자가 카드 대신 채팅 글로 퀴즈에 답하면 record_answer로 정답 여부를 기록하세요."
)


def new_conversation() -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}]


class ToolLoopError(RuntimeError):
    """The model kept calling tools without ever producing a final answer."""


def _run_tool(func, name: str, raw_args: str | None) -> dict:
    # A broken tool call should reach the model as an error it can explain,
    # not crash the whole turn.
    if func is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        return {"error": f"{name}: arguments were not valid JSON"}
    try:
        return func(**args)
    except Exception as exc:
        return {"error": f"{name} failed: {exc}"}


def run_turn(messages: list[dict], project_id: str) -> list[dict]:
    """Run one assistant turn, including any tool calls, appending to messages."""
    client = get_client()
    tool_functions = build_tool_functions(project_id)

    for _ in range(settings.max_tool_rounds):
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
            result = _run_tool(tool_functions.get(name), name, tool_call.function.arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise ToolLoopError(f"no final answer after {settings.max_tool_rounds} tool rounds")


TOOL_STATUS = {
    "search_notes": "노트를 찾고 있어요",
    "generate_quiz": "퀴즈를 만들고 있어요",
    "get_weak_topics": "약점 주제를 확인하고 있어요",
    "record_answer": "결과를 기록하고 있어요",
}


def run_turn_stream(messages: list[dict], project_id: str):
    """Same loop as run_turn, but yields ("status", text) while tools run and
    ("delta", text) as the final answer is generated. messages is updated in place."""
    client = get_client()
    tool_functions = build_tool_functions(project_id)

    for _ in range(settings.max_tool_rounds):
        stream = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            stream=True,
        )
        content = []
        calls: dict[int, dict] = {}
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                content.append(delta.content)
                yield "delta", delta.content
            # Tool calls arrive in pieces: an id and name first, then the arguments
            # JSON split across chunks, all keyed by the call's index.
            for piece in delta.tool_calls or []:
                call = calls.setdefault(piece.index, {"id": "", "name": "", "arguments": ""})
                if piece.id:
                    call["id"] = piece.id
                if piece.function and piece.function.name:
                    call["name"] = piece.function.name
                if piece.function and piece.function.arguments:
                    call["arguments"] += piece.function.arguments

        if not calls:
            messages.append({"role": "assistant", "content": "".join(content)})
            return

        ordered = [calls[i] for i in sorted(calls)]
        assistant = {
            "role": "assistant",
            "tool_calls": [
                {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in ordered
            ],
        }
        if content:
            assistant["content"] = "".join(content)
        messages.append(assistant)

        for call in ordered:
            yield "status", TOOL_STATUS.get(call["name"], "작업 중이에요")
            result = _run_tool(tool_functions.get(call["name"]), call["name"], call["arguments"])
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise ToolLoopError(f"no final answer after {settings.max_tool_rounds} tool rounds")
