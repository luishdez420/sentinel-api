from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import SessionLocal
from app.core.rate_limit import rate_limit_backend, redis_client

router = APIRouter()


@router.get("/health/live")
def liveness():
    return {"status": "ok"}


@router.get("/health")
def health():
    db_ok = True
    rate_limit_ok = True

    # DB check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    finally:
        try:
            db.close()
        except Exception:
            pass

    # Rate limit backend check
    try:
        redis_client.ping()
    except Exception:
        rate_limit_ok = False

    status = "ok" if (db_ok and rate_limit_ok) else "degraded"
    code = 200 if status == "ok" else 503

    return JSONResponse(
        {
            "status": status,
            "db": "ok" if db_ok else "down",
            "rate_limit_backend": rate_limit_backend,
            "rate_limit": "ok" if rate_limit_ok else "down",
        },
        status_code=code,
    )
