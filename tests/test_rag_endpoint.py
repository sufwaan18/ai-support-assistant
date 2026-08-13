from collections.abc import Sequence
from typing import Any

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.models import RAGSource
from app.rag_dependencies import (
    get_rag_collection,
    get_rag_encoder,
)


class FakeEncoder:
    def encode(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeCollection:
    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> None:
        return None

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str],
    ) -> dict[str, Any]:
        return {}

    def count(self) -> int:
        return 0


def test_create_rag_support_reply(
    monkeypatch: Any,
) -> None:
    def fake_generate(
        **kwargs: Any,
    ) -> tuple[str, list[RAGSource]]:
        return (
            "Contact the bank about the duplicate charge "
            "[CFPB complaint ID: 1001].",
            [
                RAGSource(
                    complaint_id="1001",
                    product="Credit card",
                    issue="Billing problem",
                    company="Example Bank",
                    date_received="2026-03-01",
                    distance=0.1,
                )
            ],
        )

    monkeypatch.setattr(
        main_module,
        "generate_grounded_support_reply",
        fake_generate,
    )
    app.dependency_overrides[get_rag_encoder] = FakeEncoder
    app.dependency_overrides[get_rag_collection] = FakeCollection

    client = TestClient(app)
    response = client.post(
        "/rag/support",
        json={
            "subject": "Duplicate card charge",
            "message": (
                "The same purchase appears twice on my statement."
            ),
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "completed"
    assert body["sources"][0]["complaint_id"] == "1001"
    assert "general customer-support" in body["disclaimer"]