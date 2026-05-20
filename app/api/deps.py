from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.jwt import decode_token
from app.core.rate_limit import check_rate_limit
from app.db.models import User
from app.db.session import SessionLocal

bearer_scheme = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = creds.credentials
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    allowed, remaining, retry_after, backend_down = check_rate_limit(user_id)

    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_retry_after = retry_after
    request.state.rate_limit_backend_down = backend_down

    if not allowed:
        headers = {"Retry-After": str(retry_after or 60)}
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded", headers=headers
        )

    return user
