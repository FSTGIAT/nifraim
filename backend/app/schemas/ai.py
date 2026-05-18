from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    history: list[ChatMessage] = []
    # Raised 8000 → 14000 to accommodate the per-customer truth blocks in
    # view_context (top-30 customers × ~120 chars each). The frontend caps at
    # 12000; this gives slack for the wrapper instructions.
    view_context: str | None = Field(default=None, max_length=14000)
