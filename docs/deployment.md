# Deployment Guide

Sentinel API is packaged as a Dockerized FastAPI service with PostgreSQL,
Redis, Alembic migrations, JSON logs, Prometheus metrics, and health checks.

## Required Environment Variables

| Variable | Required | Example | Notes |
|---|---:|---|---|
| `APP_ENV` | No | `production` | Runtime environment label. |
| `DATABASE_URL` | Yes | `postgresql+psycopg2://user:pass@host:5432/db` | PostgreSQL connection string. |
| `JWT_SECRET` | Yes | generated secret | Must be 32+ random characters. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token lifetime. |
| `REDIS_HOST` | Yes | `redis` | Redis host or managed Redis hostname. |
| `REDIS_PORT` | No | `6379` | Redis port. |
| `RATE_LIMIT` | No | `20` | Requests per rate-limit window. |
| `RATE_LIMIT_WINDOW_SECONDS` | No | `60` | Rate-limit window duration. |
| `HOST` | No | `0.0.0.0` | Container bind host. |
| `PORT` | No | `8000` | Container bind port. |

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Local Production-Like Run

Copy the example environment file and set a real `JWT_SECRET`:

```bash
cp .env.example .env
```

Start the stack:

```bash
docker compose up --build
```

The API will be available at:

- Service index: `http://localhost:8000/`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/v1/health`
- Metrics: `http://localhost:8000/metrics`

Stop and remove containers:

```bash
docker compose down
```

Remove local database volume:

```bash
docker compose down -v
```

## Container Image Behavior

The production image:

- Runs as a non-root `appuser`
- Disables Python bytecode writes
- Installs pinned dependencies from `requirements.txt`
- Runs `alembic upgrade head` before starting the API
- Starts Uvicorn with proxy header support
- Includes an HTTP health check against `/api/v1/health`

## Platform Deployment Notes

Most container platforms need the same pieces:

1. A Docker image built from this repository.
2. A managed PostgreSQL database.
3. A managed Redis instance.
4. Environment variables from the table above.
5. A public HTTP service exposing container port `8000`.

### Render

Use a Web Service backed by this repository's Dockerfile. Add managed
PostgreSQL and Redis, then set:

```text
DATABASE_URL=<managed postgres internal connection string>
REDIS_HOST=<managed redis host>
REDIS_PORT=<managed redis port>
JWT_SECRET=<generated secret>
APP_ENV=production
```

Set the health check path to:

```text
/api/v1/health
```

### Fly.io

Create a Fly app from the Dockerfile, attach Postgres and Redis-compatible
services, and configure secrets:

```bash
fly secrets set JWT_SECRET=...
fly secrets set DATABASE_URL=...
fly secrets set REDIS_HOST=...
fly secrets set REDIS_PORT=6379
```

Expose internal port `8000` and use `/api/v1/health` as the health check path.

### Railway

Create a service from the GitHub repository, add PostgreSQL and Redis plugins,
and set the required environment variables. Railway should build the Dockerfile
and route public traffic to the service port.

### AWS ECS

Build and push the image to ECR, run it as an ECS service, and use RDS
PostgreSQL plus ElastiCache Redis. Configure an Application Load Balancer target
group health check on `/api/v1/health`.

## README Screenshots

Do not use mock dashboards as proof of observability. Add screenshots only from
real deployed services, for example:

- `/docs` Swagger UI from the live URL
- `/api/v1/health` response from the live URL
- Grafana dashboard connected to real Prometheus metrics
