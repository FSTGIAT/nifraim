from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    history: list[ChatMessage] = []
    view_context: str | None = Field(default=None, max_length=8000)
    # If "agency_accountant" and the user has an agency role, swap the system
    # prompt + context to the agency-wide persona. Defaults to None so existing
    # agent flows are unchanged.
    prompt_persona: str | None = Field(default=None, max_length=40)
