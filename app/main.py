import time
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.metrics import record_request, get_metrics
from app.api.routes.health import router as health_router
from app.api.routes import auth, notes

logger = logging.getLogger("rlapi")

app = FastAPI()

app.include_router(health_router, tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(notes.router, prefix="/notes", tags=["notes"])


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response

    except Exception:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.exception(
            "unhandled_exception",
            extra={
                "event": "request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "latency_ms": latency_ms,
            },
        )
        # record as 500 so metrics are correct
        record_request(status_code=500, latency_ms=latency_ms)
        return JSONResponse(
            {"detail": "Internal Server Error", "request_id": request_id},
            status_code=500,
        )

    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        # If exception happened, we already recorded above. Prevent double count:
        if status_code != 500:
            record_request(status_code=status_code, latency_ms=latency_ms)

        logger.info(
            "request",
            extra={
                "event": "request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": latency_ms,
            },
        )


@app.middleware("http")
async def rate_limit_headers(request: Request, call_next):
    response = await call_next(request)

    remaining = getattr(request.state, "rate_limit_remaining", None)
    retry_after = getattr(request.state, "rate_limit_retry_after", None)
    backend_down = getattr(request.state, "rate_limit_backend_down", None)

    if remaining is not None:
        response.headers["X-RateLimit-Remaining"] = str(remaining)
    if retry_after is not None:
        response.headers["Retry-After"] = str(retry_after)
    if backend_down is not None:
        response.headers["X-RateLimit-Backend-Down"] = "1" if backend_down else "0"

    return response


@app.get("/metrics")
def metrics():
    return get_metrics()
