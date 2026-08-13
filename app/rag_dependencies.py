from functools import lru_cache
from pathlib import Path

from app.embeddings import (
    SentenceTransformerEncoder,
    TextEncoder,
)
from app.vector_store import (
    CollectionProtocol,
    create_persistent_collection,
)


@lru_cache
def get_rag_encoder() -> TextEncoder:
    return SentenceTransformerEncoder()


@lru_cache
def get_rag_collection() -> CollectionProtocol:
    return create_persistent_collection(
        Path("data/chroma")
    )