from types import SimpleNamespace

from src import expand


def _client(content=None, error=None):
    def create(**kwargs):
        if error:
            raise error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_returns_the_terms_the_model_proposes(monkeypatch):
    monkeypatch.setattr(expand, "get_client", lambda: _client('{"terms": ["스프린트 회고", " KPT ", ""]}'))
    assert expand.expand_query("한 주기 끝나고 되짚는 모임은?") == ["스프린트 회고", "KPT"]


def test_keeps_at_most_five_terms(monkeypatch):
    monkeypatch.setattr(expand, "get_client", lambda: _client('{"terms": ["a", "b", "c", "d", "e", "f"]}'))
    assert expand.expand_query("질문") == ["a", "b", "c", "d", "e"]


def test_ignores_non_text_terms_and_odd_shapes(monkeypatch):
    monkeypatch.setattr(expand, "get_client", lambda: _client('{"terms": [1, null, "UDP"]}'))
    assert expand.expand_query("질문") == ["UDP"]
    monkeypatch.setattr(expand, "get_client", lambda: _client("[]"))
    assert expand.expand_query("질문") == []


def test_returns_nothing_on_error(monkeypatch):
    monkeypatch.setattr(expand, "get_client", lambda: _client(error=RuntimeError("boom")))
    assert expand.expand_query("질문") == []
