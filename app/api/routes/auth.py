from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.api.schemas import (
    ErrorEnvelope,
    LoginRequest,
    RegisterRequest,
    TokenEnvelope,
    TokenResponse,
    UserEnvelope,
    UserResponse,
)
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

ERROR_RESPONSES = {
    400: {"model": ErrorEnvelope},
    401: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
}


@router.post(
    "/register",
    response_model=UserEnvelope,
    status_code=201,
    responses=ERROR_RESPONSES,
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserEnvelope(data=UserResponse(id=str(user.id), email=user.email))


@router.post("/login", response_model=TokenEnvelope, responses=ERROR_RESPONSES)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token(str(user.id))
    return TokenEnvelope(data=TokenResponse(access_token=token))


@router.get("/me", response_model=UserEnvelope, responses=ERROR_RESPONSES)
def me(current_user: User = Depends(get_current_user)):
    return UserEnvelope(
        data=UserResponse(id=str(current_user.id), email=current_user.email)
    )
