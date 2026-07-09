from pydantic import BaseModel, Field

# Bodies longer than this are truncated server-side before insert.
MAX_BODY_LEN = 4000
PREVIEW_LEN = 140


class ContactOut(BaseModel):
    """A person, as seen by ANOTHER user.

    This is the only schema in the app that crosses the user_id tenancy boundary,
    so it is a strict whitelist. Do NOT add `email`, `phone`, or `company_name` —
    the open directory would then leak every customer's contact details to every
    other customer. `username` exists precisely so people are identifiable
    without exposing an email.
    """

    id: str
    username: str
    # Seed for their generated avatar; NULL = derive from username.
    avatar_seed: str | None = None
    full_name: str | None = None
    initial: str
    online: bool = False
    unread: int = 0
    last_message_preview: str | None = None
    last_message_at: str | None = None
    last_message_from_me: bool = False


class MessageOut(BaseModel):
    id: str
    seq: int
    sender_id: str
    recipient_id: str
    body: str
    created_at: str
    # Echoed back on the send response so the client can reconcile its optimistic bubble.
    client_id: str | None = None


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=MAX_BODY_LEN)
    client_id: str | None = None


class ThreadPage(BaseModel):
    messages: list[MessageOut]
    has_more: bool = False


class PollOut(BaseModel):
    messages: list[MessageOut]
    cursor: int
    total_unread: int


class HeartbeatOut(BaseModel):
    total_unread: int
