# Deployment Guide

Sentinel API is packaged as a Dockerized FastAPI service with PostgreSQL,
Redis, Alembic migrations, JSON logs, Prometheus metrics, and health checks.

## Required Environment Variables

| Variable | Required | Example | Notes |
|---|---:|---|---|
| `APP_ENV` | No | `production` | Runtime environment label. |
| `DATABASE_URL` | Yes | `postgresql+psycopg2://user:pass@host:5432/db` | PostgreSQL connection string. |
| `REDIS_URL` | No | `redis://host:6379/0` | Redis connection string. Defaults to local Compose Redis. |
| `JWT_SECRET` | Yes | generated secret | Must be 32+ random characters. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token lifetime. |
| `RATE_LIMIT_PER_MINUTE` | No | `20` | Requests allowed per user per minute. |
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
REDIS_URL=<managed redis connection string>
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
fly secrets set REDIS_URL=...
```

Expose internal port `8000` and use `/api/v1/health` as the health check path.

This repository includes `fly.toml` for the `sentinel-api` app and a GitHub
Actions workflow at `.github/workflows/deploy-fly.yml`.

For GitHub Actions deployments:

1. Create a Fly deploy token.
2. Add it to GitHub repository secrets as `FLY_API_TOKEN`.
3. Merge to `main` or run the `Deploy to Fly` workflow manually.

Useful local checks:

```bash
flyctl auth whoami
flyctl apps list
flyctl deploy -a sentinel-api
```

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
