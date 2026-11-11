from types import SimpleNamespace

from src import gate


def _client(content=None, error=None):
    def create(**kwargs):
        if error:
            raise error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_no_chunks_cannot_answer():
    assert gate.can_answer("질문", []) is False


def test_follows_model_verdict(monkeypatch):
    chunks = [{"text": "정규화는 중복을 줄인다"}]
    monkeypatch.setattr(gate, "get_client", lambda: _client('{"answerable": false}'))
    assert gate.can_answer("트리거란", chunks) is False
    monkeypatch.setattr(gate, "get_client", lambda: _client('{"answerable": true}'))
    assert gate.can_answer("정규화란", chunks) is True


def test_reads_the_verdict_next_to_the_named_concept(monkeypatch):
    # The prompt has the model name the concept first; only "answerable" decides.
    chunks = [{"text": "UDP는 비연결형 프로토콜로"}]
    monkeypatch.setattr(gate, "get_client", lambda: _client('{"concept": "UDP", "answerable": true}'))
    assert gate.can_answer("영상 통화처럼 빠른 게 중요한 전달 규약은?", chunks) is True
    monkeypatch.setattr(gate, "get_client", lambda: _client('{"concept": "NAT", "answerable": false}'))
    assert gate.can_answer("공유기 하나로 주소를 나눠 쓰는 기술은?", chunks) is False


def test_prompt_asks_for_the_concept_before_the_verdict():
    filled = gate.PROMPT.format(ask="질문: x", context="y")
    assert filled.index('"concept"') < filled.index('"answerable"')


def test_fails_open_on_error(monkeypatch):
    monkeypatch.setattr(gate, "get_client", lambda: _client(error=RuntimeError("boom")))
    assert gate.can_answer("질문", [{"text": "x"}]) is True
