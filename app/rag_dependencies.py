from functools import lru_cache
from app.config import settings
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
        settings.rag_database_directory
    )