from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_response_contains_generated_request_id() -> None:
    response = client.get("/health")

    request_id = response.headers["X-Request-ID"]

    assert response.status_code == 200
    assert UUID(request_id)

def test_response_preserves_client_request_id() -> None:
    response = client.get(
        "/health",
        headers={"X-Request-ID": "support-request-123"},
    )

    assert response.status_code == 200
    assert (
        response.headers["X-Request-ID"]
        == "support-request-123"
    )