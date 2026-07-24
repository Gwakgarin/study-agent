import pytest

from src import sessions


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "DB_PATH", tmp_path / "sessions.db")


def test_load_session_returns_none_when_missing():
    assert sessions.load_session("does-not-exist") is None


def test_save_then_load_round_trips_messages():
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]

    sessions.save_session("abc", messages)

    assert sessions.load_session("abc") == messages


def test_save_session_upserts_existing_session():
    sessions.save_session("abc", [{"role": "system", "content": "sys"}])
    sessions.save_session("abc", [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}])

    loaded = sessions.load_session("abc")

    assert len(loaded) == 2
    assert loaded[-1] == {"role": "user", "content": "hi"}


def test_delete_session_removes_it():
    sessions.save_session("abc", [{"role": "system", "content": "sys"}])

    sessions.delete_session("abc")

    assert sessions.load_session("abc") is None
