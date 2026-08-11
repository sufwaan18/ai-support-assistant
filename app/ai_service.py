from openai import OpenAI

from app.config import settings


SYSTEM_PROMPT = (
    "You are a helpful customer-support assistant. "
    "Provide a concise, professional reply."
)


def generate_support_reply(
    subject: str,
    message: str,
    client: OpenAI | None = None,
) -> str:
    openai_client = client or OpenAI(api_key=settings.openai_api_key)

    response = openai_client.responses.create(
        model=settings.openai_model,
        instructions=SYSTEM_PROMPT,
        input=f"Subject: {subject}\nMessage: {message}",
    )

    return response.output_text
