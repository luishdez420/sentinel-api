from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,  # subject = user id
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
