import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from app.embeddings import (
    create_complaint_document,
    embed_complaints_jsonl,
)


class FakeEncoder:
    def encode(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        return [
            [float(len(text)), 0.5, 1.0]
            for text in texts
        ]


def test_create_complaint_document() -> None:
    complaint = {
        "product": "Credit card",
        "issue": "Billing problem",
        "sub_issue": "Duplicate charge",
        "narrative": (
            "The same purchase appeared twice on the statement."
        ),
    }

    document = create_complaint_document(complaint)

    assert "Product: Credit card" in document
    assert "Issue: Billing problem" in document
    assert "Sub-issue: Duplicate charge" in document
    assert "Consumer narrative:" in document


def test_embed_complaints_jsonl(tmp_path: Path) -> None:
    input_path = tmp_path / "complaints.jsonl"
    output_path = tmp_path / "embeddings" / "complaints.jsonl"

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
            "issue": "Managing an account",
            "sub_issue": None,
            "narrative": (
                "The bank charged an unexpected maintenance fee."
            ),
            "company": "Example Financial",
            "state": None,
        },
    ]

    input_path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    count = embed_complaints_jsonl(
        input_path=input_path,
        output_path=output_path,
        encoder=FakeEncoder(),
        batch_size=1,
    )

    embedded_records = [
        json.loads(line)
        for line in output_path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]

    assert count == 2
    assert len(embedded_records) == 2
    assert embedded_records[0]["complaint_id"] == "1001"
    assert len(embedded_records[0]["embedding"]) == 3
    assert embedded_records[1]["metadata"]["state"] is None


def test_embed_complaints_rejects_invalid_batch_size(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="batch_size must be at least 1",
    ):
        embed_complaints_jsonl(
            input_path=tmp_path / "input.jsonl",
            output_path=tmp_path / "output.jsonl",
            encoder=FakeEncoder(),
            batch_size=0,
        )