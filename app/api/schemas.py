from typing import Any

from pydantic import BaseModel, EmailStr, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: Any | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class RegisterRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "ada@example.com", "password": "correct-password"}]
        }
    }

    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "ada@example.com", "password": "correct-password"}]
        }
    }

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr


class UserEnvelope(BaseModel):
    data: UserResponse


class TokenEnvelope(BaseModel):
    data: TokenResponse


class NoteCreateRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [{"title": "Launch checklist", "body": "Write tests first."}]
        }
    }

    title: str
    body: str


class NoteResponse(BaseModel):
    id: str
    title: str
    body: str
    created_at: str


class NoteEnvelope(BaseModel):
    data: NoteResponse


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int
    next_offset: int | None


class NotesPageEnvelope(BaseModel):
    data: list[NoteResponse]
    meta: PageMeta


class DeleteResponse(BaseModel):
    id: str
    deleted: bool = True


class DeleteEnvelope(BaseModel):
    data: DeleteResponse
