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


def test_fails_open_on_error(monkeypatch):
    monkeypatch.setattr(gate, "get_client", lambda: _client(error=RuntimeError("boom")))
    assert gate.can_answer("질문", [{"text": "x"}]) is True
