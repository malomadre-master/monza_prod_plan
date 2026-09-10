---
name: memory-maintenance
description: Deduplicates, updates, expires, and forgets Memora entries. Use when the user says forget, забудь, update, this is outdated, after several new memories in one session, or when similar_memories are returned.
---

# Memory Maintenance

- Дубли: не создавать вторую запись. `memory_absorb` или `memory_update` существующей. При `similar_memories` — сверить id в том же project-scope; чужие id игнорировать.
- Устарело: обновить текст + `as_of`; старое решение не оставлять как current.
- «забудь X»: `memory_hybrid_search` в текущем scope → показать id и превью → `memory_delete` только своих → подтвердить список id.
- TTL: если `expires_at` < now — не использовать в retrieval; предложить удалить.
- Не запускать `memory_rebuild_embeddings` / `memory_rebuild_crossrefs` / export без явного проекта и просьбы пользователя.
- Не править записи других тенантов (`project:thermoglass`, `project:thermoglass-telegram-bot`, `rem_calcm2`, `project:memora` из этого репозитория).
