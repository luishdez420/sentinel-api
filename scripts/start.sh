#!/usr/bin/env sh
set -eu

alembic upgrade head

exec uvicorn app.main:app \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8000}" \
  --proxy-headers
