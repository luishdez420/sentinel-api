# Sentinel API

Sentinel API is a production-style backend service built with FastAPI, PostgreSQL, Redis, and Docker. The project demonstrates core backend engineering concepts such as JWT authentication, protected CRUD endpoints, database migrations, Redis-backed rate limiting, structured request logging, and operational metrics.

This project was built as a portfolio-level backend system to show practical software engineering skills beyond a basic CRUD application.

---

## Features

- JWT-based authentication
- Required strong JWT secret configuration
- Password length validation
- Secure password hashing
- PostgreSQL database persistence
- Alembic database migrations
- Protected CRUD endpoints
- Versioned API routes under `/api/v1`
- Consistent success and error response envelopes
- Paginated notes listing
- Idempotent note creation with `Idempotency-Key`
- User ownership checks for resources
- Redis-backed fixed-window rate limiting with a no-cost in-memory deployment option
- HTTP 429 responses with rate-limit headers
- Structured request logging
- `/api/v1/health/live` liveness check for platform routing
- `/api/v1/health` readiness check for PostgreSQL and the active rate-limit backend
- `/metrics` endpoint for operational visibility
- Docker Compose setup for API, PostgreSQL, and Redis
- Interactive API documentation with FastAPI Swagger UI
- GitHub Actions quality checks for pull requests
- Dependabot dependency update automation

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Language | Python |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Cache / Rate Limiting | Redis |
| Authentication | JWT |
| Password Hashing | Argon2 via Passlib |
| Containerization | Docker / Docker Compose |

---

## Security

This project intentionally treats secrets as runtime configuration:

- `.env` is ignored by Git and should never be committed.
- `.env.example` documents the required variables with safe placeholder values.
- `JWT_SECRET` is required at startup, must be at least 32 characters, and cannot
  use known placeholder values.
- Passwords are hashed with Argon2 before storage.
- Protected endpoints require a valid Bearer token.

Generate a local JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then copy `.env.example` to `.env` and replace the placeholder secret.

Minimal deployment configuration:

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
REDIS_URL=redis://host:6379/0
JWT_SECRET=replace-with-a-generated-secret
RATE_LIMIT_PER_MINUTE=20
```

For single-machine no-cost deployments, set `REDIS_URL=memory://`.

---

## CI / Pull Requests

GitHub Actions runs on every pull request and on pushes to `main`.

Current quality gates:

- `ruff check .`
- `ruff format --check`
- `pytest` integration tests against PostgreSQL and Redis

---

## Deployment

The project includes production-oriented Docker packaging:

- Non-root container user
- Startup migrations with Alembic
- Docker and Compose health checks
- Runtime environment documentation
- Deployment notes for Render, Fly.io, Railway, and AWS ECS

See [docs/deployment.md](docs/deployment.md).

When deployed, the public service index is available at `/`, with links to
`/docs`, `/api/v1/health`, and `/metrics`.

---

## Metrics and Logs

Sentinel API emits structured JSON request logs with request IDs and exposes a
Prometheus-compatible metrics endpoint at `/metrics`.

Tracked signals include:

- Request totals by method, path, and status code
- Request latency histogram buckets
- Rate-limit allow/block counters
- Rate-limit backend failure counter
- `X-Request-ID` response headers for traceability

Example metrics:

```bash
curl http://localhost:8000/metrics
```

The previous static Grafana preview was removed because it was not generated
from live data. A real dashboard screenshot should be added only after running
Grafana against the live Prometheus endpoint.

---

## API Contract

All application routes are versioned under `/api/v1`.

Examples:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/notes?limit=20&offset=0`
- `POST /api/v1/notes`
- `GET /api/v1/notes/{note_id}`
- `DELETE /api/v1/notes/{note_id}`
- `GET /api/v1/health`

Successful responses use a `data` envelope:

```json
{
  "data": {
    "id": "note-id",
    "title": "Launch checklist",
    "body": "Write tests first.",
    "created_at": "2026-05-27T12:00:00+00:00"
  }
}
```

Paginated responses include `meta`:

```json
{
  "data": [],
  "meta": {
    "limit": 20,
    "offset": 0,
    "total": 0,
    "next_offset": null
  }
}
```

Errors use an `error` envelope:

```json
{
  "error": {
    "code": "not_found",
    "message": "Note not found",
    "request_id": "request-id"
  }
}
```

Note creation supports safe retries:

```bash
curl -X POST http://localhost:8000/api/v1/notes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: create-launch-checklist" \
  -H "Content-Type: application/json" \
  -d '{"title":"Launch checklist","body":"Write tests first."}'
```

The first request creates the note with `201`. Repeating the same
`Idempotency-Key` returns the original note with `200` instead of creating a
duplicate.

---

## Testing

The test suite uses pytest and HTTPX against the FastAPI app, with PostgreSQL
and Redis provided by Docker Compose.

Start the test dependencies:

```bash
docker compose -f docker-compose.test.yml up -d --wait
```

Run the suite:

```bash
pytest
```

Clean up the test dependencies:

```bash
docker compose -f docker-compose.test.yml down -v
```

---

## Architecture

```text
Client / Swagger UI
        |
        v
  FastAPI Application
        |
        |---- Auth Layer
        |       - User registration
        |       - Login
        |       - JWT validation
        |
        |---- Protected Notes API
        |       - Create notes
        |       - List notes
        |       - View notes
        |       - Delete notes
        |       - Ownership checks
        |
        |---- PostgreSQL
        |       - users table
        |       - notes table
        |
        |---- Redis
        |       - rate limit counters
        |
        |---- Observability
                - structured logs
                - metrics endpoint
