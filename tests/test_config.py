from app.config import Settings
from pathlib import Path

def test_default_environment() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"

def test_rag_database_directory_from_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "RAG_DATABASE_DIRECTORY",
        "/app/data/chroma",
    )

    settings = Settings(_env_file=None)

    assert settings.rag_database_directory == Path(
        "/app/data/chroma"
    )