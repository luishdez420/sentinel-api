from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import SessionLocal
from app.core.rate_limit import redis_client

router = APIRouter()

@router.get("/health")
def health():
    db_ok = True
    redis_ok = True

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

    # Redis check
    try:
        redis_client.ping()
    except Exception:
        redis_ok = False

    status = "ok" if (db_ok and redis_ok) else "degraded"
    code = 200 if status == "ok" else 503

    return {"status": status, "db": "ok" if db_ok else "down", "redis": "ok" if redis_ok else "down"}, code