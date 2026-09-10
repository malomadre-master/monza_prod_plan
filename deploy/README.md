# Deploy — MONZA Production Planner

Целевой сервер: **тот же Debian**, что Fasad_Monzana / KitchenSimples / Plitka — `109.248.163.211`.  
Репозиторий: https://github.com/malomadre-master/monza_prod_plan

| | Plitka | KitchenSimples | Fasad_Monzana | **MONZA planner** |
|--|--------|----------------|---------------|-------------------|
| Каталог | — | `/opt/kitchensimples` | `/opt/fasad-monzana` | **`/opt/monza-prod-plan`** |
| Публичный порт | `:80` | `:8081` | `:8082` | **`:8083`** |
| Внутренний API | — | `:8787` | `:8788` | **`:8790`** (только localhost) |
| БД | — | — | SQLite | **Postgres 16** в Docker, порт `127.0.0.1:5433` |

Публичный URL MVP: **http://109.248.163.211:8083/**

Caddy / Let's Encrypt на `:80` **не ставим** — сломает Plitka. HTTPS и домен — после MVP, когда появится домен или свободный `:443`.

`.env` живёт только на сервере и не коммитится.

## 1. Один раз на сервере

Под root. Origin на проде — **SSH**. Нужен отдельный deploy key: GitHub вешает ключ только на одно репо.

```bash
apt-get update && apt-get install -y git openssh-client

ssh-keygen -t ed25519 -f /root/.ssh/github_deploy_monza_prod_plan -N "" -C "monza-prod-plan-deploy"

cat >> /root/.ssh/config <<'EOF'

Host github.com-monza-prod-plan
  HostName github.com
  User git
  IdentityFile /root/.ssh/github_deploy_monza_prod_plan
  IdentitiesOnly yes
EOF
chmod 600 /root/.ssh/config /root/.ssh/github_deploy_monza_prod_plan

cat /root/.ssh/github_deploy_monza_prod_plan.pub
```

Публичный ключ — в GitHub: repo Settings → Deploy keys → Add deploy key (Allow write: нет).

```bash
ssh -T git@github.com-monza-prod-plan
git clone git@github.com-monza-prod-plan:malomadre-master/monza_prod_plan.git /opt/monza-prod-plan
cd /opt/monza-prod-plan
bash deploy/setup-server.sh
```

Проверка:

```bash
curl -s http://127.0.0.1:8790/api/health
curl -s http://127.0.0.1:8083/api/health
# снаружи: http://109.248.163.211:8083/
```

Откройте порт **8083** в firewall. Не трогайте `:80`, `:8081`, `:8082`.

## 2. GitHub Actions

Как у Fasad: тот же `DEPLOY_SSH_KEY` (вход на сервер), свои Variables.

| Variable | Значение |
|----------|----------|
| `DEPLOY_HOST` | `109.248.163.211` |
| `DEPLOY_USER` | `root` |
| `DEPLOY_PORT` | `22` |
| `DEPLOY_PATH` | `/opt/monza-prod-plan` |

Secret `DEPLOY_SSH_KEY` — тот же приватный ключ, которым Actions ходят на этот сервер для Fasad (не deploy key репозитория).

После первого setup каждый успешный CI на `main` делает `git pull` + build + `docker compose up`.

## 3. Ручное обновление

```bash
cd /opt/monza-prod-plan
bash deploy/update.sh
```
