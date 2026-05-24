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
- User ownership checks for resources
- Redis-backed fixed-window rate limiting
- HTTP 429 responses with rate-limit headers
- Structured request logging
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

---

## CI / Pull Requests

GitHub Actions runs on every pull request and on pushes to `main`.

Current quality gates:

- `ruff check .`
- `ruff format --check`
- `pytest` integration tests against PostgreSQL and Redis

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
