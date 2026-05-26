import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST

from app.api.routes import auth, notes
from app.api.routes.health import router as health_router
from app.core.logging import configure_logging
from app.core.metrics import record_request, render_prometheus_metrics

configure_logging()

logger = logging.getLogger("sentinel")

app = FastAPI()

app.include_router(health_router, tags=["health"])
app.include_router(auth.router, tags=["auth"])
app.include_router(notes.router, tags=["notes"])


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.perf_counter()
    status_code = 500
    response = None

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response

    except Exception:
        latency_seconds = time.perf_counter() - start
        logger.exception(
            "unhandled_exception",
            extra={
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "latency_ms": int(latency_seconds * 1000),
            },
        )
        response = JSONResponse(
            {"detail": "Internal Server Error", "request_id": request_id},
            status_code=500,
        )
        return response

    finally:
        latency_seconds = time.perf_counter() - start
        latency_ms = int(latency_seconds * 1000)
        route = request.scope.get("route")
        metric_path = getattr(route, "path", request.url.path)

        record_request(
            method=request.method,
            path=metric_path,
            status_code=status_code,
            latency_seconds=latency_seconds,
        )

        if response is not None:
            response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            extra={
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
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
    return Response(
        content=render_prometheus_metrics(),
        media_type=CONTENT_TYPE_LATEST,
    )
