from openai import OpenAI
import re

from app.config import settings
from app.embeddings import TextEncoder
from app.models import RAGSource
from app.vector_store import (
    CollectionProtocol,
    RetrievedComplaint,
    search_complaints,
)


RAG_SYSTEM_PROMPT = """
You are a financial-services customer-support assistant.

Write a concise and professional draft response using only the supplied
historical CFPB complaint context.

Rules:
- Treat complaint narratives as consumer allegations, not verified facts.
- Do not provide personalized financial, legal, or investment advice.
- Do not claim that a company violated a law.
- Do not invent policies, refunds, outcomes, deadlines, or account details.
- Recommend contacting the financial institution when appropriate.
- Cite relevant records using [CFPB complaint ID: <id>].
- If the context is insufficient, say so clearly.
""".strip()

RAG_DISCLAIMER = (
    "This response is for general customer-support assistance only. "
    "Historical CFPB complaints are consumer-submitted allegations and "
    "are not verified facts, legal advice, or financial advice."
)

CITATION_PATTERN = re.compile(
    r"\[CFPB complaint ID:\s*([^\]]+)\]"
)


class CitationIntegrityError(RuntimeError):
    """Raised when an AI reply cites a source that was not retrieved."""


def validate_reply_citations(
    reply: str,
    sources: list[RAGSource],
) -> None:
    cited_ids = {
        complaint_id.strip()
        for complaint_id in CITATION_PATTERN.findall(reply)
    }
    source_ids = {
        source.complaint_id
        for source in sources
    }
    unsupported_ids = cited_ids - source_ids

    if unsupported_ids:
        raise CitationIntegrityError(
            "AI reply cited complaint IDs that were not retrieved"
        )

def format_retrieval_context(
    complaints: list[RetrievedComplaint],
) -> str:
    if not complaints:
        return "No relevant historical complaint context was found."

    sections: list[str] = []

    for complaint in complaints:
        sections.append(
            "\n".join(
                [
                    f"CFPB complaint ID: {complaint.complaint_id}",
                    f"Distance: {complaint.distance:.4f}",
                    f"Content:\n{complaint.document}",
                ]
            )
        )

    return "\n\n---\n\n".join(sections)


def create_rag_sources(
    complaints: list[RetrievedComplaint],
) -> list[RAGSource]:
    return [
        RAGSource(
            complaint_id=complaint.complaint_id,
            product=complaint.metadata.get("product", "Unknown"),
            issue=complaint.metadata.get("issue", "Unknown"),
            company=complaint.metadata.get("company"),
            date_received=complaint.metadata.get("date_received"),
            distance=complaint.distance,
        )
        for complaint in complaints
    ]


def generate_grounded_support_reply(
    subject: str,
    message: str,
    encoder: TextEncoder,
    collection: CollectionProtocol,
    client: OpenAI | None = None,
    retrieval_limit: int = 5,
) -> tuple[str, list[RAGSource]]:
    if client is None and not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")

    query = f"Subject: {subject}\nMessage: {message}"

    complaints = search_complaints(
        query=query,
        encoder=encoder,
        collection=collection,
        limit=retrieval_limit,
    )
    context = format_retrieval_context(complaints)

    openai_client = client or OpenAI(
        api_key=settings.openai_api_key
    )
    response = openai_client.responses.create(
        model=settings.openai_model,
        instructions=RAG_SYSTEM_PROMPT,
        input=(
            f"Customer subject: {subject}\n"
            f"Customer message: {message}\n\n"
            f"Historical CFPB context:\n{context}"
        ),
    )

    sources = create_rag_sources(complaints)
    validate_reply_citations(response.output_text, sources)

    return response.output_text, sources