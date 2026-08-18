from fastapi.testclient import TestClient

from app.access import (
    ACCESS_CODE_TTL_SECONDS,
    _access_codes,
    _issued_code_digests,
    create_access_code,
    redeem_access_code,
    valid_session,
)
from app.main import app


client = TestClient(app)


def test_access_code_creates_browser_session(monkeypatch) -> None:
    monkeypatch.setattr("app.access.settings.app_api_key", "test-master-key")
    monkeypatch.setattr("app.security.settings.app_api_key", "test-master-key")
    _access_codes.clear()
    _issued_code_digests.clear()

    generated = client.post(
        "/access/codes",
        headers={"X-API-Key": "test-master-key"},
    )
    assert generated.status_code == 200
    assert len(generated.json()["code"]) == 6

    verified = client.post(
        "/access/verify",
        json={"code": generated.json()["code"]},
    )
    assert verified.status_code == 200
    assert verified.json()["authenticated"] is True
    assert 1 <= verified.json()["expires_in_seconds"] <= 300
    assert verified.cookies.get("tytus_session")

    session = client.get("/access/session")
    assert session.json()["authenticated"] is True
    assert 1 <= session.json()["expires_in_seconds"] <= 300


def test_access_code_is_one_time_use(monkeypatch) -> None:
    monkeypatch.setattr("app.access.settings.app_api_key", "test-master-key")
    monkeypatch.setattr("app.security.settings.app_api_key", "test-master-key")
    _access_codes.clear()
    _issued_code_digests.clear()

    generated = client.post(
        "/access/codes",
        headers={"X-API-Key": "test-master-key"},
    )
    code = generated.json()["code"]

    assert client.post("/access/verify", json={"code": code}).status_code == 200
    repeated = client.post("/access/verify", json={"code": code})
    assert repeated.status_code == 401


def test_session_expires_with_original_access_code(monkeypatch) -> None:
    monkeypatch.setattr("app.access.settings.app_api_key", "test-master-key")
    monkeypatch.setattr("app.access.time.time", lambda: 1_000)
    _access_codes.clear()
    _issued_code_digests.clear()

    code = create_access_code()
    monkeypatch.setattr("app.access.time.time", lambda: 1_120)
    session = redeem_access_code(code)

    assert session.expires_at == 1_000 + ACCESS_CODE_TTL_SECONDS
    assert valid_session(session.token) is True

    monkeypatch.setattr("app.access.time.time", lambda: 1_300)
    assert valid_session(session.token) is False


def test_generated_codes_are_unique(monkeypatch) -> None:
    monkeypatch.setattr("app.access.settings.app_api_key", "test-master-key")
    _access_codes.clear()
    _issued_code_digests.clear()

    codes = {create_access_code() for _ in range(25)}

    assert len(codes) == 25
