from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app


client = TestClient(app)


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

def test_create_ai_support_reply() -> None:
    with patch(
        "app.main.generate_support_reply",
        return_value="Please request another password reset email.",
    ) as mock_generate:
        response = client.post(
            "/support/reply",
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
