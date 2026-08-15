from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any
import pytest
from app.models import RAGSource
from app.rag_service import (
    CitationIntegrityError,
    RAG_DISCLAIMER,
    create_rag_sources,
    format_retrieval_context,
    generate_grounded_support_reply,
    validate_reply_citations,
)
from app.vector_store import RetrievedComplaint


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
        return {
            "ids": [["1001"]],
            "documents": [
                [
                    "Product: Credit card\n"
                    "Issue: Billing problem\n"
                    "Consumer narrative: Duplicate charge."
                ]
            ],
            "metadatas": [
                [
                    {
                        "product": "Credit card",
                        "issue": "Billing problem",
                        "company": "Example Bank",
                        "date_received": "2026-03-01",
                    }
                ]
            ],
            "distances": [[0.1]],
        }

    def count(self) -> int:
        return 1


class FakeResponses:
    def __init__(self) -> None:
        self.input: str | None = None
        self.instructions: str | None = None

    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
    ) -> SimpleNamespace:
        self.input = input
        self.instructions = instructions

        return SimpleNamespace(
            output_text=(
                "Please contact the bank about the duplicate charge "
                "[CFPB complaint ID: 1001]."
            )
        )


class FakeOpenAI:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_format_retrieval_context() -> None:
    complaint = RetrievedComplaint(
        complaint_id="1001",
        document="A duplicate credit-card charge.",
        distance=0.1,
        metadata={
            "product": "Credit card",
            "issue": "Billing problem",
        },
    )

    context = format_retrieval_context([complaint])

    assert "CFPB complaint ID: 1001" in context
    assert "A duplicate credit-card charge." in context


def test_create_rag_sources() -> None:
    complaint = RetrievedComplaint(
        complaint_id="1001",
        document="A duplicate credit-card charge.",
        distance=0.1,
        metadata={
            "product": "Credit card",
            "issue": "Billing problem",
        },
    )

    sources = create_rag_sources([complaint])

    assert sources[0].complaint_id == "1001"
    assert sources[0].product == "Credit card"
    assert sources[0].company is None


def test_generate_grounded_support_reply() -> None:
    client = FakeOpenAI()

    reply, sources = generate_grounded_support_reply(
        subject="Duplicate card charge",
        message=(
            "The same purchase appears twice on my card statement."
        ),
        encoder=FakeEncoder(),
        collection=FakeCollection(),
        client=client,
        retrieval_limit=1,
    )

    assert "[CFPB complaint ID: 1001]" in reply
    assert sources[0].complaint_id == "1001"
    assert client.responses.input is not None
    assert "Historical CFPB context" in client.responses.input
    assert client.responses.instructions is not None
    assert "not verified facts" in client.responses.instructions
    assert "not verified facts" in RAG_DISCLAIMER

def test_rejects_citation_not_present_in_sources() -> None:
    sources = [
        RAGSource(
            complaint_id="1001",
            product="Credit card",
            issue="Billing problem",
            company="Example Bank",
            date_received="2026-03-01",
            distance=0.1,
        )
    ]

    with pytest.raises(
        CitationIntegrityError,
        match="were not retrieved",
    ):
        validate_reply_citations(
            reply=(
                "Contact the bank "
                "[CFPB complaint ID: invented-9999]."
            ),
            sources=sources,
        )