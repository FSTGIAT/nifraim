from pydantic import BaseModel, EmailStr, Field

USERNAME_PATTERN = r'^[a-z0-9_]{3,32}$'


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    username: str = Field(pattern=USERNAME_PATTERN)


class UsernameUpdate(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)


class AvatarUpdate(BaseModel):
    # Free-form seed string chosen from the picker; the renderer hashes it.
    avatar_seed: str = Field(min_length=1, max_length=64)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    avatar_seed: str | None = None
    full_name: str | None
    phone: str | None = None
    is_active: bool = False
    is_admin: bool = False

    model_config = {"from_attributes": True}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class UserAdminOut(BaseModel):
    id: str
    email: str
    full_name: str | None
    phone: str | None
    company_name: str | None
    is_active: bool
    is_admin: bool
    created_at: str

    model_config = {"from_attributes": True}


class UserAdminUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None


class UserAdminCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    phone: str | None = None
    company_name: str | None = None
    is_admin: bool = False


class AgentStatusOut(BaseModel):
    id: str
    email: str
    full_name: str | None
    company_name: str | None
    is_active: bool
    worker_online: bool
    last_seen: str | None = None        # ISO 8601
    hostname: str | None = None
    current_job: str | None = None
