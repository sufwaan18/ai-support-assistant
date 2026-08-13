import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from app.runtime_pipeline import (
    RuntimeIndexSummary,
    build_vector_index,
    write_runtime_summary,
)


class FakeEncoder:
    def encode(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        return [
            [float(index), 0.5, 1.0]
            for index, _ in enumerate(texts, start=1)
        ]


class FakeCollection:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}

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
        return {}

    def count(self) -> int:
        return len(self.records)


def write_source_dataset(output_path: Path) -> None:
    records = [
        {
            "complaint_id": "1001",
            "date_received": "2026-03-01",
            "product": "Credit card",
            "issue": "Billing problem",
            "sub_issue": "Duplicate charge",
            "narrative": (
                "The same purchase appeared twice on my statement."
            ),
            "company": "Example Bank",
            "state": "TX",
        },
        {
            "complaint_id": "1002",
            "date_received": "2026-03-02",
            "product": "Checking or savings account",
            "issue": "Unexpected fee",
            "sub_issue": None,
            "narrative": (
                "The bank charged an unexpected maintenance fee."
            ),
            "company": "Example Financial",
            "state": None,
        },
    ]

    output_path.write_text(
        "".join(
            json.dumps(record) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def test_build_vector_index(tmp_path: Path) -> None:
    source_path = tmp_path / "complaints.jsonl"
    embedded_path = tmp_path / "embedded.jsonl"
    database_directory = tmp_path / "chroma"
    collection = FakeCollection()

    write_source_dataset(source_path)

    summary = build_vector_index(
        source_path=source_path,
        embedded_path=embedded_path,
        database_directory=database_directory,
        encoder=FakeEncoder(),
        collection=collection,
        embedding_batch_size=1,
        indexing_batch_size=1,
    )

    assert summary.embedded_records == 2
    assert summary.indexed_records == 2
    assert summary.collection_records == 2
    assert collection.count() == 2
    assert embedded_path.exists()


def test_build_vector_index_requires_source(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="Processed CFPB dataset not found",
    ):
        build_vector_index(
            source_path=tmp_path / "missing.jsonl",
            embedded_path=tmp_path / "embedded.jsonl",
            database_directory=tmp_path / "chroma",
            encoder=FakeEncoder(),
            collection=FakeCollection(),
        )


def test_write_runtime_summary(tmp_path: Path) -> None:
    summary = RuntimeIndexSummary(
        source_file="data/processed/complaints.jsonl",
        embedded_file=(
            "data/processed/embedded_complaints.jsonl"
        ),
        database_directory="data/chroma",
        embedded_records=100,
        indexed_records=100,
        collection_records=100,
    )
    output_path = tmp_path / "index_summary.json"

    result = write_runtime_summary(
        summary,
        output_path,
    )
    saved = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert result == output_path
    assert saved["indexed_records"] == 100
    assert saved["collection_records"] == 100