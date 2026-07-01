from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.metrics import record_audit_log_written
from app.db.models import AuditLog

logger = logging.getLogger("sentinel")


def write_audit_log(
    db: Session,
    *,
    event_type: str,
    user_id: object | None = None,
    resource_type: str | None = None,
    resource_id: object | None = None,
    request: Request | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        audit_log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            metadata_=metadata,
        )
        db.add(audit_log)
        db.commit()
        record_audit_log_written()
    except Exception:
        db.rollback()
        logger.exception(
            "audit_log_write_failed",
            extra={"event": "audit_log", "event_type": event_type},
        )
