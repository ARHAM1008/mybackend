"""
Authentication schemas for request/response validation.
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password (min 6 chars)")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    bio: str = ""
    avatar_url: str = ""
    skill_level: str = "beginner"

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


# Resolve forward reference
TokenResponse.model_rebuild()
