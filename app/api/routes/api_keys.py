import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.schemas import (
    ApiKeyCreateEnvelope,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyEnvelope,
    ApiKeyResponse,
    ApiKeysEnvelope,
    ErrorEnvelope,
)
from app.core.api_keys import generate_api_key
from app.core.audit import write_audit_log
from app.core.metrics import record_api_key_created, record_api_key_revoked
from app.db.models import ApiKey, User

router = APIRouter(prefix="/api-keys", tags=["api keys"])

ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    429: {"model": ErrorEnvelope},
}


def _api_key_response(api_key: ApiKey) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        prefix=api_key.prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at.isoformat(),
        last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        revoked_at=api_key.revoked_at.isoformat() if api_key.revoked_at else None,
    )


@router.post(
    "",
    response_model=ApiKeyCreateEnvelope,
    status_code=201,
    responses=ERROR_RESPONSES,
)
def create_api_key(
    data: ApiKeyCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raw_api_key, prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=data.name,
        prefix=prefix,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    record_api_key_created()
    write_audit_log(
        db,
        event_type="api_key_created",
        user_id=current_user.id,
        resource_type="api_key",
        resource_id=api_key.id,
        request=request,
        metadata={"prefix": api_key.prefix, "name": api_key.name},
    )

    return ApiKeyCreateEnvelope(
        data=ApiKeyCreateResponse(
            id=str(api_key.id),
            name=api_key.name,
            prefix=api_key.prefix,
            api_key=raw_api_key,
            is_active=api_key.is_active,
            created_at=api_key.created_at.isoformat(),
        )
    )


@router.get("", response_model=ApiKeysEnvelope, responses=ERROR_RESPONSES)
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_keys = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return ApiKeysEnvelope(data=[_api_key_response(api_key) for api_key in api_keys])


@router.delete(
    "/{key_id}",
    response_model=ApiKeyEnvelope,
    responses=ERROR_RESPONSES,
)
def revoke_api_key(
    key_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if api_key.is_active:
        api_key.is_active = False
        api_key.revoked_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        db.refresh(api_key)

        record_api_key_revoked()
        write_audit_log(
            db,
            event_type="api_key_revoked",
            user_id=current_user.id,
            resource_type="api_key",
            resource_id=api_key.id,
            request=request,
            metadata={"prefix": api_key.prefix, "name": api_key.name},
        )

    return ApiKeyEnvelope(data=_api_key_response(api_key))
