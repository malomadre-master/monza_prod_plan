---
name: privacy-and-secrets
description: Blocks secrets and sensitive data from Memora. Use before every memory_create or memory_absorb, and when content might contain tokens, passwords, .env, keys, payment data, or personal data.
---

# Privacy and secrets

Никогда не сохранять в Memora:

- API keys, токены, пароли, cookies, приватные ключи, connection strings;
- содержимое `.env`;
- платёжные реквизиты;
- персональные/чувствительные документы без явного согласия;
- данные третьих лиц, если не нужны задаче;
- медицинские, юридические, финансовые сведения без явного «запомни».

Если пользователь прислал секрет вместе с «запомни» — сохранить только несекретный факт («токен лежит в env, не в git»), сам секрет не писать. Сказать, что секрет не запомнен.

Не логировать полный текст воспоминаний и секреты в ответы/трейсы.
