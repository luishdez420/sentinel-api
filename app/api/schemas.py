from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: EmailStr

class NoteCreateRequest(BaseModel):
    title: str
    body: str

class NoteResponse(BaseModel):
    id: str
    title: str
    body: str
    created_at: str
