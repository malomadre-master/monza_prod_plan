# MONZA Production Planner

Планирование заказов мебельного производства. ТЗ и план: [`docs/project-plan.md`](docs/project-plan.md).  
Репозиторий: https://github.com/malomadre-master/monza_prod_plan

## Стек

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Postgres 16
- Frontend: React 18, TypeScript, Vite, Mantine (PWA-адаптив под ПК и телефон)
- Деплой: Docker Compose (API + Postgres) + **nginx хоста на :8083**

Прод — **тот же Debian**, что Fasad_Monzana. Не занимаем `:80` / `:8081` / `:8082`. Подробности: [`deploy/README.md`](deploy/README.md).

## Локально

Нужны Docker, Python 3.12, Node 22.

```powershell
copy .env.example .env
docker compose up -d db
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
uvicorn app.main:app --host 127.0.0.1 --port 8790 --reload
```

В другом терминале:

```powershell
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173/ — Vite проксирует `/api` на `:8790`.

Первый вход (если пользователей ещё нет): **admin** / **admin**. Смените пароль на сервере через `BOOTSTRAP_ADMIN_PASSWORD` до первого запуска или добавьте сотрудников в разделе «Сотрудники». Заказы вводят роли admin и планировщик.
