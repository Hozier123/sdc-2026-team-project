from app.config import Settings


def test_env_overrides_dotenv_and_secrets_hidden(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("DATABASE_URL=postgresql://file:local_secret@localhost/db\nDEMO_MODE=true\n")
    monkeypatch.setenv("DATABASE_URL", "postgresql://env:env_secret@localhost/db")
    settings = Settings(_env_file=dotenv)
    assert settings.database_url.get_secret_value().startswith("postgresql://env:")
    assert "env_secret" not in repr(settings)
    assert "local_secret" not in repr(settings)
