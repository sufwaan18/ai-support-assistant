import json
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


DEFAULT_EMBEDDING_MODEL = (
    "sentence-transformers/all-MiniLM-L6-v2"
)


class TextEncoder(Protocol):
    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class SentenceTransformerEncoder:
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def encode(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        embeddings = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embeddings.tolist()


class EmbeddedComplaint(BaseModel):
    complaint_id: str = Field(min_length=1)
    document: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1)
    metadata: dict[str, str | None]


def create_complaint_document(
    complaint: dict[str, object],
) -> str:
    product = str(complaint["product"])
    issue = str(complaint["issue"])
    sub_issue = complaint.get("sub_issue")
    narrative = str(complaint["narrative"])

    sections = [
        f"Product: {product}",
        f"Issue: {issue}",
    ]

    if sub_issue:
        sections.append(f"Sub-issue: {sub_issue}")

    sections.append(f"Consumer narrative: {narrative}")

    return "\n".join(sections)


def read_jsonl_batch(
    input_file: object,
    batch_size: int,
) -> list[dict[str, object]]:
    batch: list[dict[str, object]] = []

    for line in input_file:
        if not line.strip():
            continue

        batch.append(json.loads(line))

        if len(batch) >= batch_size:
            break

    return batch


def embed_complaints_jsonl(
    input_path: Path,
    output_path: Path,
    encoder: TextEncoder,
    batch_size: int = 32,
) -> int:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    embedded_count = 0

    with (
        input_path.open("r", encoding="utf-8") as input_file,
        output_path.open("w", encoding="utf-8") as output_file,
    ):
        while True:
            complaints = read_jsonl_batch(
                input_file,
                batch_size,
            )

            if not complaints:
                break

            documents = [
                create_complaint_document(complaint)
                for complaint in complaints
            ]
            embeddings = encoder.encode(documents)

            if len(embeddings) != len(complaints):
                raise ValueError(
                    "encoder returned an unexpected embedding count"
                )

            for complaint, document, embedding in zip(
                complaints,
                documents,
                embeddings,
                strict=True,
            ):
                record = EmbeddedComplaint(
                    complaint_id=str(
                        complaint["complaint_id"]
                    ),
                    document=document,
                    embedding=embedding,
                    metadata={
                        "product": str(complaint["product"]),
                        "issue": str(complaint["issue"]),
                        "sub_issue": (
                            str(complaint["sub_issue"])
                            if complaint.get("sub_issue")
                            else None
                        ),
                        "company": str(complaint["company"]),
                        "state": (
                            str(complaint["state"])
                            if complaint.get("state")
                            else None
                        ),
                        "date_received": str(
                            complaint["date_received"]
                        ),
                    },
                )

                output_file.write(
                    json.dumps(
                        record.model_dump(mode="json")
                    )
                    + "\n"
                )
                embedded_count += 1

    return embedded_count