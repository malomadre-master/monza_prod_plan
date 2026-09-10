---
name: memora-isolation
description: Isolates Prod_Plan_MONZA memories with unique tags project:prod-plan-monza and prefix [MONZA]. Use before any Memora write or search in Prod_Plan_MONZA.
---

# Memora: Prod_Plan_MONZA

Общая БД `146.66.177.230` / MCP `http://127.0.0.1:8080/mcp`.

Этот репозиторий — **планирование производства MONZA**, не Thermoglass MES, не Telegram-бот, не Fasad_Monzana.

| Поле | Значение |
|---|---|
| prefix | `[MONZA]` |
| фильтр поиска | `project:prod-plan-monza` |
| доп. теги | `prod-plan-monza/project` |
| metadata.project | `prod-plan-monza` |

Не читать и не писать `[TG]`, `[THERMOGLASS-TELEGRAM-BOT]`, `[MEMORA]`, `project:thermoglass`, `project:thermoglass-telegram-bot`, `project:memora`, `rem_calcm2/`.
Если MCP недоступен — поднять туннель, не обходить.
