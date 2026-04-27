from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AgencySummary(BaseModel):
    id: str
    name: str
    slug: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None
    phone: str | None = None
    is_active: bool = False
    is_admin: bool = False
    role: str = "agent"
    agency: AgencySummary | None = None
    impersonating: bool = False

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
