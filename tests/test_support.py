from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "test-app-api-key"}


def test_create_support_request() -> None:
    response = client.post(
        "/support",
        json={
            "subject": "Cannot reset password",
            "message": "The password reset email never arrives.",
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "received",
        "subject": "Cannot reset password",
    }

def test_rejects_short_support_message() -> None:
    response = client.post(
        "/support",
        json={
            "subject": "Password issue",
            "message": "Too short",
        },
    )

    assert response.status_code == 422


def test_create_ai_support_reply(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.security.settings.app_api_key",
        "test-app-api-key",
    )
    with patch(
        "app.main.generate_support_reply",
        return_value="Please request another password reset email.",
    ) as mock_generate:
        response = client.post(
            "/support/reply",
            headers=AUTH_HEADERS,
            json={
                "subject": "Cannot reset password",
                "message": "The password reset email never arrives.",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "subject": "Cannot reset password",
        "reply": "Please request another password reset email.",
    }
    mock_generate.assert_called_once_with(
        subject="Cannot reset password",
        message="The password reset email never arrives.",
    )

def test_ai_support_reply_without_openai_key_returns_503(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.security.settings.app_api_key",
        "test-app-api-key",
    )
    with patch(
        "app.main.generate_support_reply",
        side_effect=ValueError("OPENAI_API_KEY is required"),
    ):
        response = client.post(
            "/support/reply",
            headers=AUTH_HEADERS,
            json={
                "subject": "Cannot reset password",
                "message": "The password reset email never arrives.",
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "AI service is not configured",
    }
