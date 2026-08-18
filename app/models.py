from pydantic import BaseModel, Field


class SupportRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=100)
    message: str = Field(min_length=10, max_length=2000)


class SupportResponse(BaseModel):
    status: str
    subject: str
    reply: str


class AccessCodeRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class RAGSource(BaseModel):
    complaint_id: str = Field(min_length=1)
    product: str
    issue: str
    company: str | None = None
    date_received: str | None = None
    distance: float = Field(ge=0)


class RAGSupportResponse(BaseModel):
    status: str
    subject: str
    reply: str
    sources: list[RAGSource]
    disclaimer: str
