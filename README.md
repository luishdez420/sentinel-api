# Sentinel API

Sentinel API is a production-style backend service built with FastAPI, PostgreSQL, Redis, and Docker. The project demonstrates core backend engineering concepts such as JWT authentication, protected CRUD endpoints, database migrations, Redis-backed rate limiting, structured request logging, and operational metrics.

This project was built as a portfolio-level backend system to show practical software engineering skills beyond a basic CRUD application.

---

## Features

- JWT-based authentication
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
