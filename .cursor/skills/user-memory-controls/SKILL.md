---
name: user-memory-controls
description: Lets the user list, inspect, edit, and delete their Memora memories in the current project scope. Use when they ask what you remember, show memories, change a memory, or forget something.
---

# User memory controls

Человек всегда может увидеть, изменить и удалить память текущего проекта.

- «что ты помнишь» / список: `memory_list` с `tags_all` текущего project-тега, compact preview, показать id.
- «покажи N»: `memory_get` только если теги совпадают со scope; иначе ответить «нет в этом проекте» без содержимого чужой записи.
- «исправь на …»: `memory_update` в том же scope, обновить `as_of`.
- «забудь»: search → подтверждение списком id → `memory_delete`.
- Не предлагать глобальный dump всей БД. Не экспортировать другие проекты.

После изменения кратко подтвердить: id, действие, новый превью (без секретов).
