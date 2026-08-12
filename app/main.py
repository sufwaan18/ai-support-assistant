from fastapi import FastAPI, HTTPException, status

from app.ai_service import generate_support_reply
from app.models import SupportRequest, SupportResponse

from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware

configure_logging()

app = FastAPI(
    title="AI Support Assistant",
    version="0.1.0",
)

app.add_middleware(RequestLoggingMiddleware)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}

@app.post("/support", status_code=202)
def create_support_request(request: SupportRequest) -> dict[str, str]:
    return {
        "status": "received",
        "subject": request.subject,
    }


@app.post("/support/reply", response_model=SupportResponse)
def create_support_reply(request: SupportRequest) -> SupportResponse:
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

    return SupportResponse(
        status="completed",
        subject=request.subject,
        reply=reply,
    )
