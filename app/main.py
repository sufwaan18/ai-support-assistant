from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
import time
from fastapi import Cookie, Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import RateLimitError


from app.ai_service import generate_support_reply
from app.access import (
    ACCESS_CODE_TTL_SECONDS,
    SESSION_COOKIE_NAME,
    create_access_code,
    redeem_access_code,
    require_chat_access,
    session_remaining_seconds,
)
from app.config import settings
from app.embeddings import TextEncoder
from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware
from app.rate_limit import enforce_ai_rate_limit
from app.models import (
    RAGSupportResponse,
    AccessCodeRequest,
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

STATIC_DIRECTORY = Path(__file__).parent / "static"
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIRECTORY),
    name="static",
)


@app.get("/", include_in_schema=False)
def support_assistant_ui() -> FileResponse:
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/admin", include_in_schema=False)
def access_code_admin_ui() -> FileResponse:
    return FileResponse(STATIC_DIRECTORY / "admin.html")


@app.post("/access/codes")
def generate_access_code(
    _: None = Depends(require_api_key),
) -> dict[str, int | str]:
    return {
        "code": create_access_code(),
        "expires_in_seconds": ACCESS_CODE_TTL_SECONDS,
    }


@app.post("/access/verify")
def verify_access_code(request: AccessCodeRequest) -> JSONResponse:
    session = redeem_access_code(request.code)
    remaining_seconds = max(
        1,
        session.expires_at - int(time.time()),
    )
    response = JSONResponse({
        "authenticated": True,
        "expires_in_seconds": remaining_seconds,
    })
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.token,
        max_age=remaining_seconds,
        httponly=True,
        secure=settings.environment != "development",
        samesite="strict",
    )
    return response


@app.get("/access/session")
def access_session(
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, bool | int]:
    remaining_seconds = session_remaining_seconds(session_token)
    return {
        "authenticated": remaining_seconds > 0,
        "expires_in_seconds": remaining_seconds,
    }


@app.post("/access/logout")
def access_logout() -> JSONResponse:
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.environment != "development",
        samesite="strict",
    )
    return response


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
    _: None = Depends(require_chat_access),
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
    _: None = Depends(require_chat_access),
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
