#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/monza-prod-plan}"
cd "$APP_DIR"

git pull --ff-only origin main
( cd frontend && npm ci && npm run build )
docker compose build
docker compose up -d --remove-orphans
nginx -t && systemctl reload nginx

if curl -fsS "http://127.0.0.1:8790/api/health" >/dev/null \
  || curl -fsS "http://127.0.0.1:8083/api/health" >/dev/null; then
  echo "update ok"
else
  echo "health check failed" >&2
  exit 1
fi
