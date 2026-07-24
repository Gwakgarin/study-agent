"""Shared fixtures: fake OpenAI client so tests never hit the network or need an API key."""

from types import SimpleNamespace

import pytest


class FakeEmbeddings:
    def __init__(self, vectors_by_text=None, default_dim=8):
        self.vectors_by_text = vectors_by_text or {}
        self.default_dim = default_dim
        self.calls = []

    def create(self, model, input):
        self.calls.append(input)
        data = [
            SimpleNamespace(embedding=self.vectors_by_text.get(text, [0.0] * self.default_dim))
            for text in input
        ]
        return SimpleNamespace(data=data)


class FakeChatCompletions:
    def __init__(self, responses):
        # responses: list of SimpleNamespace(choices=[...]) returned in order, one per call
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeOpenAI:
    def __init__(self, vectors_by_text=None, chat_responses=None):
        self.embeddings = FakeEmbeddings(vectors_by_text)
        self.chat = SimpleNamespace(completions=FakeChatCompletions(chat_responses or []))


def make_message_response(content):
    """Build a fake chat.completions.create response with no tool calls."""
    message = SimpleNamespace(
        role="assistant",
        content=content,
        tool_calls=None,
        model_dump=lambda exclude_none=True: {"role": "assistant", "content": content},
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_tool_call_response(tool_calls):
    """tool_calls: list of (id, name, arguments_json_str)."""
    calls = [
        SimpleNamespace(id=tc_id, function=SimpleNamespace(name=name, arguments=args))
        for tc_id, name, args in tool_calls
    ]
    message = SimpleNamespace(
        role="assistant",
        content=None,
        tool_calls=calls,
        model_dump=lambda exclude_none=True: {
            "role": "assistant",
            "tool_calls": [
                {"id": c.id, "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in calls
            ],
        },
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def fake_openai_factory():
    return FakeOpenAI
