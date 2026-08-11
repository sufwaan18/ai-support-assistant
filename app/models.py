from pydantic import BaseModel, Field


class SupportRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=100)
    message: str = Field(min_length=10, max_length=2000)

class SupportResponse(BaseModel):
    status: str
    subject: str
    reply: str