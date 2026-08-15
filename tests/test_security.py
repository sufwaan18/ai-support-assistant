from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
VALID_REQUEST = {
    "subject": "Duplicate credit card charge",
    "message": "The same purchase appears twice on my statement.",
}


def test_health_check_does_not_require_api_key() -> None:
    response = client.get("/health")

    assert response.status_code == 200


def test_protected_endpoint_rejects_missing_api_key(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.security.settings.app_api_key",
        "test-app-api-key",
    )

    response = client.post("/support/reply", json=VALID_REQUEST)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing API key"
    }


def test_protected_endpoint_rejects_incorrect_api_key(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.security.settings.app_api_key",
        "test-app-api-key",
    )

    response = client.post(
        "/support/reply",
        headers={"X-API-Key": "incorrect-key"},
        json=VALID_REQUEST,
    )

    assert response.status_code == 401


def test_protected_endpoint_reports_missing_configuration(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.security.settings.app_api_key",
        "",
    )

    response = client.post(
        "/support/reply",
        headers={"X-API-Key": "any-value"},
        json=VALID_REQUEST,
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "API authentication is not configured"
    }
