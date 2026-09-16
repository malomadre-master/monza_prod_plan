#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/monza-prod-plan}"
SKIP_GIT_PULL="${SKIP_GIT_PULL:-0}"
cd "$APP_DIR"

if [[ "$SKIP_GIT_PULL" != "1" ]]; then
  git pull --ff-only origin main
fi

docker compose up -d --build --remove-orphans

if docker network inspect telemonza_web_net >/dev/null 2>&1; then
  cid="$(docker compose ps -q api || true)"
  if [[ -n "$cid" ]] && ! docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{println $k}}{{end}}' "$cid" | grep -qx telemonza_web_net; then
    docker network connect telemonza_web_net "$cid"
  fi
fi

install -m 644 deploy/nginx-monza-prod-plan.conf /etc/nginx/sites-available/monza-prod-plan
nginx -t && systemctl reload nginx

if [[ -e /opt/docker-stack/bin/wait-health.sh ]]; then
  bash /opt/docker-stack/bin/wait-health.sh
else
  ok=0
  for _ in 1 2 3 4 5 6 7 8; do
    if curl -fsS "http://127.0.0.1:8790/api/health" >/dev/null \
      || curl -fsS "http://127.0.0.1:8083/api/health" >/dev/null; then
      ok=1
      break
    fi
    sleep 3
  done
  if [[ "$ok" -ne 1 ]]; then
    echo "health check failed" >&2
    exit 1
  fi
fi

echo "update ok"
