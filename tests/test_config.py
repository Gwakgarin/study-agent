from src.config import Settings


def test_settings_defaults_when_no_env_vars(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CHAT_MODEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.openai_api_key is None
    assert settings.chat_model == "gpt-4o-mini"
    assert settings.chunk_size == 800
    assert settings.cors_origins == ["http://localhost:5173"]


def test_settings_reads_overrides_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CHAT_MODEL", "gpt-4o")
    monkeypatch.setenv("CHUNK_SIZE", "500")

    settings = Settings(_env_file=None)

    assert settings.openai_api_key == "sk-test"
    assert settings.chat_model == "gpt-4o"
    assert settings.chunk_size == 500
