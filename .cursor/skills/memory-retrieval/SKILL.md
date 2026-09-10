---
name: memory-retrieval
description: Retrieves scoped Memora context before answering. Use at the start of a task, before architecture/preference answers, and whenever the user asks what we decided, how we do X, or to recall prior context.
---

# Memory Retrieval

Перед содержательным ответом по проекту:

1. Scope только текущего workspace. Поиск без project-тега запрещён.
2. Вызови `memory_digest` или `memory_hybrid_search` с `tags_all: ["<project-tag>"]`.
3. Для Prod_Plan_MONZA тег: `project:prod-plan-monza`.
4. Отбрось хиты с чужим prefix/тегом, `kind=temporary` с прошлым `expires_at`, и записи без `as_of` если они противоречат более новым.
5. Не выдавай память как истину. Формат: «По памяти (id N, as_of DATE, confidence C): … Если устарело — скажи.»
6. Не подмешивай другие проекты, даже если semantic search вернул похожие id.
7. Кэш агента: ключ `{project_tag}:search:{hash}`. Без prefix не кэшировать.
8. Если MCP недоступен — отвечай без памяти и попроси туннель. Не выдумывай «что мы помнили».
