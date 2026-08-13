import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.embeddings import TextEncoder


DEFAULT_COLLECTION_NAME = "cfpb_complaints"


class CollectionProtocol(Protocol):
    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> Any:
        ...

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str],
    ) -> dict[str, Any]:
        ...

    def count(self) -> int:
        ...


class RetrievedComplaint(BaseModel):
    complaint_id: str = Field(min_length=1)
    document: str = Field(min_length=1)
    distance: float = Field(ge=0)
    metadata: dict[str, str]


def create_persistent_collection(
    database_path: Path,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> CollectionProtocol:
    import chromadb

    database_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(database_path))

    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def normalize_metadata(
    metadata: dict[str, object],
) -> dict[str, str]:
    return {
        key: str(value)
        for key, value in metadata.items()
        if value is not None
    }


def index_embedded_complaints(
    input_path: Path,
    collection: CollectionProtocol,
    batch_size: int = 100,
) -> int:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    indexed_count = 0
    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []

    def write_batch() -> None:
        nonlocal indexed_count

        if not ids:
            return

        collection.upsert(
            ids=ids.copy(),
            embeddings=embeddings.copy(),
            documents=documents.copy(),
            metadatas=metadatas.copy(),
        )
        indexed_count += len(ids)

        ids.clear()
        embeddings.clear()
        documents.clear()
        metadatas.clear()

    with input_path.open("r", encoding="utf-8") as input_file:
        for line in input_file:
            if not line.strip():
                continue

            record = json.loads(line)

            ids.append(str(record["complaint_id"]))
            embeddings.append(
                [float(value) for value in record["embedding"]]
            )
            documents.append(str(record["document"]))
            metadatas.append(
                normalize_metadata(record["metadata"])
            )

            if len(ids) >= batch_size:
                write_batch()

    write_batch()

    return indexed_count


def search_complaints(
    query: str,
    encoder: TextEncoder,
    collection: CollectionProtocol,
    limit: int = 5,
) -> list[RetrievedComplaint]:
    if not query.strip():
        raise ValueError("query must not be blank")

    if limit < 1:
        raise ValueError("limit must be at least 1")

    query_embeddings = encoder.encode([query])

    if len(query_embeddings) != 1:
        raise ValueError(
            "encoder returned an unexpected embedding count"
        )

    result = collection.query(
        query_embeddings=query_embeddings,
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    return [
        RetrievedComplaint(
            complaint_id=str(complaint_id),
            document=str(document),
            distance=float(distance),
            metadata={
                str(key): str(value)
                for key, value in metadata.items()
            },
        )
        for complaint_id, document, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
            strict=True,
        )
    ]