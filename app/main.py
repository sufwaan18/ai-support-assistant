from fastapi import FastAPI
from app.models import SupportRequest

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