from fastapi.testclient import TestClient

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


