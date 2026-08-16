from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, status
from openai import RateLimitError


from app.ai_service import generate_support_reply
from app.config import settings
from app.embeddings import TextEncoder
from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware
from app.rate_limit import enforce_ai_rate_limit
from app.models import (
    RAGSupportResponse,
    SupportRequest,
    SupportResponse,
)
from app.rag_dependencies import (
    get_rag_collection,
    get_rag_encoder,
)
from app.rag_service import (
    CitationIntegrityError,
    RAG_DISCLAIMER,
    generate_grounded_support_reply,
)
from app.s3_bootstrap import bootstrap_rag_snapshot
from app.security import require_api_key
from app.vector_store import CollectionProtocol


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    bootstrap_rag_snapshot(
        bucket=settings.rag_snapshot_s3_bucket,
        key=settings.rag_snapshot_s3_key,
        database_directory=settings.rag_database_directory,
    )

    yield

app = FastAPI(
    title="AI Support Assistant",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/support", status_code=202)
def create_support_request(
    request: SupportRequest,
) -> dict[str, str]:
    return {
        "status": "received",
        "subject": request.subject,
    }


@app.post(
    "/support/reply",
    response_model=SupportResponse,
)
def create_support_reply(
    request: SupportRequest,
    _: None = Depends(require_api_key),
    _rate_limit: None = Depends(enforce_ai_rate_limit),
) -> SupportResponse:
    try:
        reply = generate_support_reply(
            subject=request.subject,
            message=request.message,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured",
        ) from error
    except RateLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is temporarily unavailable",
        ) from error

    return SupportResponse(
        status="completed",
        subject=request.subject,
        reply=reply,
    )


@app.post(
    "/rag/support",
    response_model=RAGSupportResponse,
)
def create_rag_support_reply(
    request: SupportRequest,
    _: None = Depends(require_api_key),
    _rate_limit: None = Depends(enforce_ai_rate_limit),
    encoder: TextEncoder = Depends(get_rag_encoder),
    collection: CollectionProtocol = Depends(
        get_rag_collection
    ),
) -> RAGSupportResponse:
    try:
        reply, sources = generate_grounded_support_reply(
            subject=request.subject,
            message=request.message,
            encoder=encoder,
            collection=collection,
        )

    except CitationIntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI response failed citation validation",
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not configured",
        ) from error

    return RAGSupportResponse(
        status="completed",
        subject=request.subject,
        reply=reply,
        sources=sources,
        disclaimer=RAG_DISCLAIMER,
    )
