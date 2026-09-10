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

`github.com-monza-prod-plan` — **не DNS**, а Host-алиас в `/root/.ssh/config`. Без блока `Host` clone падает с `Could not resolve hostname`. Ключ Fasad/KitchenSimples сюда не подойдёт.

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

Два разных ключа:

| Ключ | Зачем | Куда |
|------|--------|------|
| `/root/.ssh/github_deploy_monza_prod_plan` | сервер тянет GitHub | Deploy keys репозитория |
| `DEPLOY_SSH_KEY` | Actions заходят по SSH на telemonza | Secret репозитория; pubkey в `/root/.ssh/authorized_keys` |

Variables (уже можно задать открыто):

| Variable | Значение |
|----------|----------|
| `DEPLOY_HOST` | `109.248.163.211` |
| `DEPLOY_USER` | `root` |
| `DEPLOY_PORT` | `22` |
| `DEPLOY_PATH` | `/opt/monza-prod-plan` |

`DEPLOY_SSH_KEY` — **не** deploy key репозитория. Отдельный ключ для входа Actions на сервер. Публичную часть один раз добавить:

```bash
# на telemonza
mkdir -p /root/.ssh
echo 'ssh-ed25519 … monza-prod-plan-actions' >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

После этого каждый успешный CI на `main` (или **Actions → Deploy to Debian → Run workflow**) собирает фронт **на раннере GitHub**, копирует `frontend/dist` на сервер и там только `git pull` + `docker compose`. На telemonza `npm run build` при деплое не запускается — 2 CPU не тянут Vite за отведённое время.

## 3. Ручное обновление

```bash
cd /opt/monza-prod-plan
# полная сборка на сервере (медленно):
bash deploy/update.sh
# если dist уже приехал из Actions:
SKIP_FRONTEND_BUILD=1 bash deploy/update.sh
```
