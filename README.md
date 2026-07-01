# Sentinel API

Sentinel API is a production-style FastAPI backend for authenticated note
management. It is intentionally scoped like a real service rather than a demo:
versioned routes, JWT and API-key authentication, ownership checks, database
migrations, per-user rate limiting, audit logs, structured logs, Prometheus
metrics, Docker packaging, CI, and a deployable Fly.io configuration.

The goal of the project is to show backend engineering judgment: how to protect
user data, keep API behavior consistent, make failures observable, and document
the tradeoffs behind operational decisions.

## What Problem This Solves

Many portfolio APIs stop at basic CRUD. Sentinel API treats that CRUD surface as
the beginning of the engineering problem:

- Users need secure registration, login, API keys, and authenticated access.
- Notes must be isolated by owner so one user cannot read another user's data.
- Clients need predictable response shapes, pagination, and retry-safe writes.
- Operators need health checks, request IDs, metrics, and logs when something
  breaks.
- The service should run locally with Docker Compose and deploy cleanly without
  committing secrets.

In short, this project models the kind of backend service a team could extend
instead of throw away.

## Architecture

```text
Client / Swagger UI
        |
        v
FastAPI app
        |
        |-- API v1 router
        |     |-- auth: register, login, current user
        |     |-- api keys: create, list, revoke
        |     |-- notes: create, list, get, delete
        |     |-- health: liveness and readiness
        |
        |-- middleware
        |     |-- request ID propagation
        |     |-- structured JSON request logging
        |     |-- Prometheus request metrics
        |     |-- rate-limit response headers
        |
        |-- SQLAlchemy + Alembic
        |     |-- PostgreSQL users, notes, api_keys, audit_logs
        |
        |-- rate-limit backend
              |-- Redis for local/distributed deployments
              |-- memory:// for no-cost single-machine Fly deployments
```

Core routes:

| Route | Purpose |
|---|---|
| `GET /` | Service index with links to docs, health, and metrics. |
| `POST /api/v1/auth/register` | Create a user with a hashed password. |
| `POST /api/v1/auth/login` | Return a JWT access token. |
| `GET /api/v1/auth/me` | Return the authenticated user. |
| `POST /api/v1/api-keys` | Create an API key and return the full value once. |
| `GET /api/v1/api-keys` | List safe API-key metadata. |
| `DELETE /api/v1/api-keys/{key_id}` | Revoke an API key. |
| `POST /api/v1/notes` | Create a note, optionally idempotent. |
| `GET /api/v1/notes` | List notes with `limit` and `offset` pagination. |
| `GET /api/v1/notes/{note_id}` | Fetch one owned note. |
| `DELETE /api/v1/notes/{note_id}` | Delete one owned note. |
| `GET /api/v1/health/live` | Liveness check for platform routing. |
| `GET /api/v1/health` | Readiness check for database and rate-limit backend. |
| `GET /metrics` | Prometheus-compatible metrics. |

## Security Model

Sentinel API treats security as runtime behavior, not just documentation.

- Passwords are hashed with Argon2 through Passlib before storage.
- JWTs are signed with `HS256` and validated on protected routes.
- API keys are generated with secure random bytes and stored only as hashes.
- API key responses expose only a short prefix after creation.
- `JWT_SECRET` is required at startup, must be at least 32 characters, and cannot
  use known placeholder values.
- `.env` is ignored by Git; `.env.example` contains only safe placeholders.
- Notes are always queried by both note ID and authenticated user ID to enforce
  ownership.
- Errors use a consistent envelope with `code`, `message`, and `request_id`.
- Request IDs are returned in `X-Request-ID` and included in JSON logs.

Example error response:

```json
{
  "error": {
    "code": "not_found",
    "message": "Note not found",
    "request_id": "request-id"
  }
}
```

## API Key Management

API keys let scripts, integrations, and external clients call protected routes
without reusing an interactive login token.

Create a key with a JWT:

```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"ci-script"}'
```

The response includes the full API key only once:

```json
{
  "data": {
    "id": "api-key-id",
    "name": "ci-script",
    "prefix": "safe-prefix",
    "api_key": "sentinel_safe-prefix_secret-value",
    "is_active": true,
    "created_at": "2026-07-01T12:00:00+00:00"
  }
}
```

Use the key with `X-API-Key`:

```bash
curl http://localhost:8000/api/v1/notes \
  -H "X-API-Key: $SENTINEL_API_KEY"
```

List keys without exposing secrets:

```bash
curl http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN"
```

Revoke a key:

```bash
curl -X DELETE http://localhost:8000/api/v1/api-keys/$KEY_ID \
  -H "Authorization: Bearer $TOKEN"
```

Revoked keys are marked inactive and can no longer authenticate requests.

## Rate Limiting Strategy

Authenticated routes use a fixed-window rate limit. JWT requests are keyed by
user ID, while API-key requests are keyed by API key ID.

Behavior:

- JWT requests default to `60` requests per minute.
- API-key requests default to `100` requests per minute.
- Allowed requests receive `X-RateLimit-Remaining`.
- Responses include `X-RateLimit-Limit`.
- Blocked requests return HTTP `429` with `Retry-After`.
- Redis failures fail open so users are not locked out by a cache outage.
- Metrics record allowed requests, blocked requests, and backend failures.
- `memory://` is supported for no-cost single-machine deployments.

The Redis backend is the better choice for multi-machine deployments because it
shares counters across instances. The memory backend is intentionally documented
as a portfolio-friendly Fly.io option: it avoids paid services, but counters are
per process and reset on restart.

## Database Schema

The schema is intentionally small but includes production-relevant constraints.

| Table | Column | Purpose |
|---|---|---|
| `users` | `id` | UUID primary key. |
| `users` | `email` | Unique, indexed login identifier. |
| `users` | `password_hash` | Argon2 password hash. |
| `notes` | `id` | UUID primary key. |
| `notes` | `user_id` | Foreign key to `users.id`, indexed for ownership queries. |
| `notes` | `title` | Required note title, limited to 200 characters. |
| `notes` | `body` | Required note body. |
| `notes` | `idempotency_key` | Optional client retry key. |
| `notes` | `created_at` | Timezone-aware creation timestamp. |
| `api_keys` | `id` | UUID primary key. |
| `api_keys` | `user_id` | Owner ID. |
| `api_keys` | `key_hash` | Secure hash of the full API key. |
| `api_keys` | `name` | User-friendly key name. |
| `api_keys` | `prefix` | Short display and lookup prefix. |
| `api_keys` | `is_active` | Revocation status. |
| `api_keys` | `last_used_at` | Last successful API-key auth timestamp. |
| `api_keys` | `revoked_at` | Revocation timestamp. |
| `audit_logs` | `id` | UUID primary key. |
| `audit_logs` | `user_id` | User associated with the event, when available. |
| `audit_logs` | `event_type` | Event name such as `api_key_created`. |
| `audit_logs` | `resource_type` | Resource category such as `api_key` or `note`. |
| `audit_logs` | `resource_id` | Resource identifier. |
| `audit_logs` | `ip_address` | Request client IP, when available. |
| `audit_logs` | `user_agent` | Request user agent, when available. |
| `audit_logs` | `metadata` | Additional event context. |
| `audit_logs` | `created_at` | Timezone-aware event timestamp. |

The `notes` table has a unique constraint on `(user_id, idempotency_key)`. This
lets a client safely retry `POST /api/v1/notes` with the same
`Idempotency-Key` without creating duplicate notes.

## API Contract

All application routes are versioned under `/api/v1`. Successful responses use
a `data` envelope:

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

Retry-safe note creation:

```bash
curl -X POST http://localhost:8000/api/v1/notes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: create-launch-checklist" \
  -H "Content-Type: application/json" \
  -d '{"title":"Launch checklist","body":"Write tests first."}'
```

The first request creates the note with `201`. Repeating the same
`Idempotency-Key` returns the original note with `200`.

## Observability

Sentinel API emits structured JSON request logs and exposes Prometheus metrics
at `/metrics`.

Tracked signals:

- HTTP request totals by method, route, and status code.
- Request latency histogram buckets.
- Rate-limit allow/block counters.
- Rate-limit backend failure counter.
- API-key auth success and failure counters.
- API-key creation and revocation counters.
- Audit-log write counters.
- Request IDs in both logs and response headers.

Audit logs are written for:

- API key creation.
- API key revocation.
- Invalid API key attempts.
- Rate-limit violations.
- Note creation.
- Note deletion.

Audit logging is best-effort: failures are logged but do not crash the request
path.

Health checks are split by operational purpose:

- `/api/v1/health/live` answers whether the process can serve HTTP.
- `/api/v1/health` answers whether PostgreSQL and the active rate-limit backend
  are reachable.

The README does not include a fake Grafana screenshot. A dashboard screenshot
should only be added after Grafana is connected to live Prometheus data.

## Testing Strategy

The test suite uses pytest and HTTPX against the FastAPI ASGI app. PostgreSQL
and Redis are provided by Docker Compose for integration-style coverage.

Covered areas:

- Registration, login, and current-user auth flow.
- Duplicate registration and password validation.
- Missing and invalid JWT failures.
- Notes CRUD and user ownership boundaries.
- Pagination behavior.
- Idempotent note creation.
- Rate limiting and rate-limit headers.
- API key creation, listing, revocation, authentication, and hashed storage.
- Invalid and revoked API key failures.
- Audit log creation for security and resource events.
- Health checks.
- Prometheus metrics and JSON log formatting.
- Alembic migrations reaching the latest head.
- In-memory rate-limit backend behavior.

Run test dependencies:

```bash
docker compose -f docker-compose.test.yml up -d --wait
```

Run checks:

```bash
ruff check .
ruff format --check
pytest
```

Clean up:

```bash
docker compose -f docker-compose.test.yml down -v
```

## Local Development

Create an environment file:

```bash
cp .env.example .env
```

Generate a local JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Start the app with PostgreSQL and Redis:

```bash
docker compose up --build
```

Useful local URLs:

- API docs: `http://localhost:8000/docs`
- Service index: `http://localhost:8000/`
- Readiness: `http://localhost:8000/api/v1/health`
- Metrics: `http://localhost:8000/metrics`

## Deployment

The project includes Docker packaging and deployment notes for Fly.io, Render,
Railway, and AWS ECS.

Production-oriented packaging includes:

- Non-root container user.
- Alembic migrations at startup.
- Docker health checks.
- Runtime environment documentation.
- GitHub Actions checks for linting, formatting, and tests.
- Dependabot automation for dependency updates.

See [docs/deployment.md](docs/deployment.md).

Minimal deployment configuration:

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
REDIS_URL=memory://
JWT_SECRET=replace-with-a-generated-secret
RATE_LIMIT_PER_MINUTE=20
API_KEY_RATE_LIMIT_PER_MINUTE=100
```

Use a real Redis URL instead of `memory://` when running multiple API instances
or when rate-limit counters must survive restarts.

## Tradeoffs

- **Fixed-window rate limiting:** Simple to explain and test, but bursts can
  occur near window boundaries. A sliding-window or token-bucket algorithm would
  smooth traffic better.
- **Fail-open rate limiting:** Keeps the API usable during cache failures, but
  weakens abuse protection while the backend is unavailable.
- **In-memory backend for Fly.io:** Avoids paid Redis for a portfolio
  deployment, but counters reset on restart and are not shared across machines.
- **Startup migrations:** Simple for a small service, but larger systems may
  prefer a separate migration job to avoid deploy-time coupling.
- **JWT-only auth:** Keeps the service stateless, but token revocation would
  require an additional denylist or session store. API keys cover automation
  use cases but still need revocation and audit logging.
- **No frontend:** The deployed app focuses on backend engineering. FastAPI docs
  provide an interactive interface, but a polished UI could improve demos.

## Future Work

- Add load testing with k6 or Locust and publish measured RPS and p95 latency.
- Add coverage reporting to CI.
- Add update endpoints for notes and soft-delete behavior.
- Add refresh tokens or token revocation for more complete auth lifecycle
  management.
- Add API key scopes so keys can be limited to specific operations.
- Add a real Grafana dashboard connected to Prometheus data.
- Add Terraform or Pulumi for repeatable infrastructure provisioning.
- Add OpenTelemetry traces for cross-service observability.
- Add a small frontend or API demo page for non-technical reviewers.
