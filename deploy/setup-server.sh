#!/usr/bin/env bash
# One-time setup on the shared Debian host (same as Fasad_Monzana).
# Usage as root after clone into /opt/monza-prod-plan:
#   bash deploy/setup-server.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/monza-prod-plan}"
APP_USER="${APP_USER:-www-data}"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y git curl ca-certificates nginx

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

cd "$APP_DIR"

if [[ ! -f .env ]]; then
  JWT="$(openssl rand -hex 32)"
  PG="$(openssl rand -hex 16)"
  cat > .env <<EOF
POSTGRES_USER=monza
POSTGRES_PASSWORD=${PG}
POSTGRES_DB=monza
POSTGRES_PORT=5433
DATABASE_URL=postgresql+psycopg://monza:${PG}@db:5432/monza
JWT_SECRET=${JWT}
API_HOST=0.0.0.0
API_PORT=8790
CORS_ORIGINS=http://127.0.0.1:8083,http://localhost:8083,http://109.248.163.211:8083
EOF
  chmod 640 .env
  chown root:"$APP_USER" .env
fi

if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

( cd frontend && npm ci && npm run build )

docker compose build
docker compose up -d

install -m 644 deploy/monza-prod-plan.service /etc/systemd/system/monza-prod-plan.service
install -m 644 deploy/nginx-monza-prod-plan.conf /etc/nginx/sites-available/monza-prod-plan
ln -sfn /etc/nginx/sites-available/monza-prod-plan /etc/nginx/sites-enabled/monza-prod-plan

nginx -t
systemctl daemon-reload
systemctl enable --now monza-prod-plan
systemctl reload nginx

echo "OK: http://$(hostname -I | awk '{print $1}'):8083/"
echo "Health: curl -s http://127.0.0.1:8083/api/health"
echo "Do not bind :80 / :8081 / :8082"
