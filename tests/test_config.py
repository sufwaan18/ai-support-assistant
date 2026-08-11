from app.config import Settings


def test_default_environment() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"