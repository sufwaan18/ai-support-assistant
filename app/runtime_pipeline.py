import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.embeddings import TextEncoder, embed_complaints_jsonl
from app.vector_store import (
    CollectionProtocol,
    create_persistent_collection,
    index_embedded_complaints,
)


class RuntimeIndexSummary(BaseModel):
    source_file: str
    embedded_file: str
    database_directory: str
    embedded_records: int = Field(ge=0)
    indexed_records: int = Field(ge=0)
    collection_records: int = Field(ge=0)


def write_runtime_summary(
    summary: RuntimeIndexSummary,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            summary.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return output_path


def build_vector_index(
    source_path: Path,
    embedded_path: Path,
    database_directory: Path,
    encoder: TextEncoder,
    collection: CollectionProtocol | None = None,
    embedding_batch_size: int = 32,
    indexing_batch_size: int = 100,
) -> RuntimeIndexSummary:
    if not source_path.is_file():
        raise FileNotFoundError(
            f"Processed CFPB dataset not found: {source_path}"
        )

    if embedding_batch_size < 1:
        raise ValueError(
            "embedding_batch_size must be at least 1"
        )

    if indexing_batch_size < 1:
        raise ValueError(
            "indexing_batch_size must be at least 1"
        )

    embedded_records = embed_complaints_jsonl(
        input_path=source_path,
        output_path=embedded_path,
        encoder=encoder,
        batch_size=embedding_batch_size,
    )

    vector_collection = collection or create_persistent_collection(
        database_path=database_directory,
    )

    indexed_records = index_embedded_complaints(
        input_path=embedded_path,
        collection=vector_collection,
        batch_size=indexing_batch_size,
    )

    if indexed_records != embedded_records:
        raise ValueError(
            "embedded and indexed record counts do not match"
        )

    return RuntimeIndexSummary(
        source_file=str(source_path),
        embedded_file=str(embedded_path),
        database_directory=str(database_directory),
        embedded_records=embedded_records,
        indexed_records=indexed_records,
        collection_records=vector_collection.count(),
    )