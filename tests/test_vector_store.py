import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from app.vector_store import (
    index_embedded_complaints,
    normalize_metadata,
    search_complaints,
)


class FakeEncoder:
    def encode(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeCollection:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, object]] = {}

    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> None:
        for complaint_id, embedding, document, metadata in zip(
            ids,
            embeddings,
            documents,
            metadatas,
            strict=True,
        ):
            self.records[complaint_id] = {
                "embedding": embedding,
                "document": document,
                "metadata": metadata,
            }

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str],
    ) -> dict[str, Any]:
        assert query_embeddings == [[0.1, 0.2, 0.3]]
        assert include == [
            "documents",
            "metadatas",
            "distances",
        ]

        return {
            "ids": [["1001"]][:n_results],
            "documents": [
                [
                    "Product: Credit card\n"
                    "Issue: Billing problem\n"
                    "Consumer narrative: Duplicate charge."
                ]
            ][:n_results],
            "metadatas": [
                [
                    {
                        "product": "Credit card",
                        "issue": "Billing problem",
                    }
                ]
            ][:n_results],
            "distances": [[0.12]][:n_results],
        }

    def count(self) -> int:
        return len(self.records)


def test_normalize_metadata_removes_missing_values() -> None:
    metadata = normalize_metadata(
        {
            "product": "Credit card",
            "state": None,
            "date_received": "2026-03-01",
        }
    )

    assert metadata == {
        "product": "Credit card",
        "date_received": "2026-03-01",
    }


def test_index_embedded_complaints(tmp_path: Path) -> None:
    input_path = tmp_path / "embedded.jsonl"
    records = [
        {
            "complaint_id": "1001",
            "document": "First complaint document",
            "embedding": [0.1, 0.2, 0.3],
            "metadata": {
                "product": "Credit card",
                "issue": "Billing problem",
                "state": "TX",
            },
        },
        {
            "complaint_id": "1002",
            "document": "Second complaint document",
            "embedding": [0.4, 0.5, 0.6],
            "metadata": {
                "product": "Checking or savings account",
                "issue": "Unexpected fee",
                "state": None,
            },
        },
    ]
    input_path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    collection = FakeCollection()

    indexed_count = index_embedded_complaints(
        input_path=input_path,
        collection=collection,
        batch_size=1,
    )

    assert indexed_count == 2
    assert collection.count() == 2
    assert collection.records["1002"]["metadata"] == {
        "product": "Checking or savings account",
        "issue": "Unexpected fee",
    }


def test_search_complaints() -> None:
    results = search_complaints(
        query="My credit card was charged twice",
        encoder=FakeEncoder(),
        collection=FakeCollection(),
        limit=1,
    )

    assert len(results) == 1
    assert results[0].complaint_id == "1001"
    assert results[0].distance == pytest.approx(0.12)
    assert results[0].metadata["product"] == "Credit card"


def test_search_rejects_blank_query() -> None:
    with pytest.raises(
        ValueError,
        match="query must not be blank",
    ):
        search_complaints(
            query="   ",
            encoder=FakeEncoder(),
            collection=FakeCollection(),
        )


def test_index_rejects_invalid_batch_size(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="batch_size must be at least 1",
    ):
        index_embedded_complaints(
            input_path=tmp_path / "embedded.jsonl",
            collection=FakeCollection(),
            batch_size=0,
        )