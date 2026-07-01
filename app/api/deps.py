import datetime

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.api_keys import extract_api_key_prefix, verify_api_key
from app.core.audit import write_audit_log
from app.core.jwt import decode_token
from app.core.metrics import (
    record_api_key_auth_failed,
    record_api_key_auth_success,
    record_rate_limit,
)
from app.core import rate_limit as rate_limit_module
from app.db.models import ApiKey, User
from app.db.session import SessionLocal

bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    user: User | None = None
    auth_method = "jwt"
    rate_limit_subject_type = "user"
    rate_limit_subject_id: object | None = None
    active_rate_limit = rate_limit_module.RATE_LIMIT

    if creds is not None:
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
        rate_limit_subject_id = user_id

    elif x_api_key:
        auth_method = "api_key"
        rate_limit_subject_type = "api_key"
        prefix = extract_api_key_prefix(x_api_key)
        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.prefix == prefix, ApiKey.is_active.is_(True))
            .first()
            if prefix
            else None
        )

        if (
            not api_key
            or api_key.revoked_at
            or not verify_api_key(x_api_key, api_key.key_hash)
        ):
            record_api_key_auth_failed()
            write_audit_log(
                db,
                event_type="api_key_auth_failed",
                request=request,
                metadata={"prefix": prefix},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
            )

        user = db.query(User).filter(User.id == api_key.user_id).first()
        if user:
            api_key.last_used_at = datetime.datetime.now(datetime.UTC)
            db.commit()

        request.state.api_key_id = str(api_key.id)
        rate_limit_subject_id = api_key.id
        active_rate_limit = rate_limit_module.API_KEY_RATE_LIMIT
        record_api_key_auth_success()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token or API key",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    if rate_limit_subject_id is None:
        rate_limit_subject_id = user.id

    allowed, remaining, retry_after, backend_down, limit = (
        rate_limit_module.check_rate_limit(
            rate_limit_subject_id,
            subject_type=rate_limit_subject_type,
            limit=active_rate_limit,
        )
    )
    record_rate_limit(
        allowed=allowed, backend_down=backend_down, auth_method=auth_method
    )

    request.state.auth_method = auth_method
    request.state.rate_limit_limit = limit
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_retry_after = retry_after
    request.state.rate_limit_backend_down = backend_down

    if not allowed:
        headers = {"Retry-After": str(retry_after or 60)}
        write_audit_log(
            db,
            event_type="rate_limit_exceeded",
            user_id=user.id,
            resource_type=rate_limit_subject_type,
            resource_id=rate_limit_subject_id,
            request=request,
            metadata={"auth_method": auth_method, "limit": limit},
        )
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded", headers=headers
        )

    return user
