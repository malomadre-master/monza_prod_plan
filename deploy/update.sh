#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/monza-prod-plan}"
SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-0}"
cd "$APP_DIR"
git pull --ff-only origin main

if [[ "$SKIP_FRONTEND_BUILD" != "1" ]]; then
  ( cd frontend && npm ci && npm run build )
elif [[ ! -f frontend/dist/index.html ]]; then
  echo "frontend/dist is missing; build in CI or run without SKIP_FRONTEND_BUILD=1" >&2
  exit 1
fi

docker compose build
docker compose up -d --remove-orphans
nginx -t && systemctl reload nginx

ok=0
for _ in 1 2 3 4 5 6 7 8; do
  if curl -fsS "http://127.0.0.1:8790/api/health" >/dev/null \
    || curl -fsS "http://127.0.0.1:8083/api/health" >/dev/null; then
    ok=1
    break
  fi
  sleep 3
done

if [[ "$ok" -eq 1 ]]; then
  echo "update ok"
else
  echo "health check failed" >&2
  exit 1
fi
