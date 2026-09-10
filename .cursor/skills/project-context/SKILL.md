---
name: project-context
description: Resolves Memora project scope from the workspace path. Use before any Memora read or write, when switching repos, or when the user says this belongs to project N.
---

# Project context

Один MCP / одна БД на `146.66.177.230`. Scope задаёт workspace, не клиентский «поставь другой project».

| Workspace path | prefix первой строки | tags_all | доп. теги |
|---|---|---|---|
| thermoglass-production-automation | `[TG]` | `project:thermoglass` | слой + источник |
| ThermoGlassTGbot | `[THERMOGLASS-TELEGRAM-BOT]` | `project:thermoglass-telegram-bot` | `telegram-bot/thermoglass-customer`, `repo:malomadre-ThermoGlass_TG_bot` |
| rem_calcm2 | — | `rem_calcm2/project` | metadata `project: rem_calcm2` |
| Prod_Plan_MONZA | `[MONZA]` | `project:prod-plan-monza` | `prod-plan-monza/project`, metadata `project: prod-plan-monza` |
| работа над самим Memora | `[MEMORA]` | `project:memora` | — |

`memora/documents`, `memora/todos`, `memora/issues`, `memora/sections`, `memora/project` — таксономия продукта, не tenant.

«это относится к проекту N» — писать только если N совпадает с текущим workspace или пользователь явно переключает работу. Иначе спроси.

Неясен проект — не пиши. Fasad_Monzana — отдельный workspace, не смешивать с этим тенантом.
