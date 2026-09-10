---
name: memory-extraction
description: Extracts only durable useful facts from a conversation into Memora. Use before memory_create, memory_absorb, or when the user says remember, запомни, always do, don't use, or states a lasting preference or decision.
---

# Memory Extraction

Перед любой записью в Memora:

1. Прочитай политику: `docs/memory-policy.md`.
2. Определи project-scope по workspace (см. skill `project-context`). Нет scope — не пиши.
3. Отфильтруй кандидатов. Сохраняй только:
   - предпочтения (язык, формат, инструменты, ограничения);
   - долгосрочные факты (роль, стек, процессы, инфраструктура без секретов);
   - подтверждённые технические решения;
   - цели/этапы/дедлайны с датой;
   - явные «запомни» / «всегда так» / «не используй X» / «в этом проекте Y».
4. Не сохраняй: разовые вопросы, приветствия, chain-of-thought, предположения, отладку, полный чат, секреты, платежи, чужие ПДн, мед/юр/фин без явного «запомни».
5. «не запоминай» — стоп. «это временно» — только `kind=temporary` + `expires_at`. «забудь» — skill `memory-maintenance`.
6. Классификация: `durable` | `temporary` | `contextual`. Contextual по умолчанию не писать в БД.
7. Confidence < 0.8 — спроси, не пиши.
8. Одна память = один факт. Первая строка = prefix проекта. Сжать, не копировать диалог.
9. Пиши через `memory_absorb` (дедуп) в текущем project-scope. `memory_create` — только если absorb недоступен; тогда `suggest_similar: true`.
10. Metadata: `kind`, `confidence`, `source`, `as_of`, `project`; теги project + `memory/<kind>` + слой `arch|decision|constraint|glossary|integration|open-question`.
