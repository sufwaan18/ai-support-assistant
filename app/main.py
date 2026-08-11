from fastapi import FastAPI
from app.ai_service import generate_support_reply
from app.models import SupportRequest, SupportResponse


app = FastAPI(
    title="AI Support Assistant",
    version="0.1.0",
)


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
    reply = generate_support_reply(
        subject=request.subject,
        message=request.message,
    )

    return SupportResponse(
        status="completed",
        subject=request.subject,
        reply=reply,
    )
