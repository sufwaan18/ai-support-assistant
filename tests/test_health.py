from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_startup_bootstraps_rag_snapshot() -> None:
    with patch(
        "app.main.bootstrap_rag_snapshot"
    ) as mock_bootstrap:
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    mock_bootstrap.assert_called_once_with(
        bucket=settings.rag_snapshot_s3_bucket,
        key=settings.rag_snapshot_s3_key,
        database_directory=settings.rag_database_directory,
    )