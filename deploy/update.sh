#!/usr/bin/env bash
# Docker deploy from /opt/monza-prod-plan: frontend build + compose up -d --build
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/monza-prod-plan}"
SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-0}"
SKIP_GIT_PULL="${SKIP_GIT_PULL:-0}"
BRANCH="${BRANCH:-main}"

cd "$APP_DIR"
git config --global --add safe.directory "$APP_DIR" || true
if [[ "$SKIP_GIT_PULL" != "1" ]]; then
  git fetch origin
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
fi

if [[ "$SKIP_FRONTEND_BUILD" != "1" ]]; then
  ( cd frontend && npm ci && npm run build )
elif [[ ! -f frontend/dist/index.html ]]; then
  echo "frontend/dist is missing; build in CI or run without SKIP_FRONTEND_BUILD=1" >&2
  exit 1
fi

docker compose up -d --build --remove-orphans

# Keep shared web network for sibling services (idempotent)
docker network connect telemonza_web_net monza-prod-plan-api-1 2>/dev/null || true

if [[ -f deploy/nginx-monza-prod-plan.conf ]]; then
  install -m 644 deploy/nginx-monza-prod-plan.conf /etc/nginx/sites-available/monza-prod-plan
  nginx -t && systemctl reload nginx
fi

/opt/docker-stack/bin/wait-health.sh 3 \
  "http://127.0.0.1:8790/api/health" \
  "http://127.0.0.1:8083/api/health"

echo "Deploy OK (Docker)"
echo "HEAD=$(git -C "$APP_DIR" rev-parse --short HEAD)"
