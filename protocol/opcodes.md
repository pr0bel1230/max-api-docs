# Опкоды MAX API

Все опкоды протестированы на `api.oneme.ru:443` (TCP, ver=10).
Совместимы с WebSocket (ver=11, JSON).

Подробная документация по группам опкодов:
- [Аутентификация](auth.md) — INIT, LOGIN
- [Сообщения](messaging.md) — MSG_SEND, MSG_DELETE, GET_HISTORY, GET_MESSAGE
- [Чаты](chats.md) — GET_CHATS, CHAT_ACTION, GET_STATS
- [Контакты](contacts.md) — GET_CONTACTS, профиль
- [Файлы](files.md) — FILE_UPLOAD, прикрепление файлов
- [Push-уведомления](push.md) — NOTIF_PRESENCE, NOTIF_ATTACH

## Таблица опкодов

### Системные

| Опкод | Название | cmd | Payload запроса | Документация |
|-------|----------|-----|-----------------|-------------|
| 6 | INIT | 1 | `{userAgent, deviceId}` | [auth.md](auth.md) |
| 19 | LOGIN | 1 | `{token, interactive, chatsCount, ...}` | [auth.md](auth.md) |

### Сообщения

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 49 | GET_HISTORY | 1 | [messaging.md](messaging.md) |
| 64 | MSG_SEND | 1 | [messaging.md](messaging.md) |
| 65 | MSG_TYPING | 1 | [messaging.md](messaging.md) |
| 66 | MSG_DELETE | 1 | [messaging.md](messaging.md) |
| 67 | MSG_EDIT | 3* | [messaging.md](messaging.md) |
| 68 | MSG_FWD | 3 | — |
| 71 | GET_MESSAGE | 1 | [messaging.md](messaging.md) |
| 92 | MSG_DELETE_RANGE | ? | [messaging.md](messaging.md) |

\* — на момент исследования. Возможно, требуется другой payload.

### Чаты и контакты

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 32 | GET_CONTACTS | 1 | [contacts.md](contacts.md) |
| 53 | GET_CHATS | 1 | [chats.md](chats.md) |
| 72 | CHAT_ACTION | 1 | [chats.md](chats.md) |
| 74 | GET_STATS | 1 | [chats.md](chats.md) |

### Файлы

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 87 | FILE_UPLOAD | 1 | [files.md](files.md) |

### Push-уведомления (cmd=0)

| Опкод | Название | Описание | Документация |
|-------|----------|----------|-------------|
| 132 | NOTIF_PRESENCE | Изменение статуса присутствия | [push.md](push.md) |
| 136 | NOTIF_ATTACH | Подтверждение загрузки файла | [files.md](files.md) |
| 140 | NOTIF_MSG_DELETE_RANGE | Уведомление о массовом удалении | [push.md](push.md) |
| 142 | NOTIF_MSG_DELETE | Уведомление об удалении сообщения | [push.md](push.md) |

## Коды ответа cmd

| cmd | Значение |
|-----|----------|
| 0 | Push-уведомление (сервер → клиент) |
| 1 | Успешный ответ (ACK) |
| 3 | Ошибка |

**Важно:** cmd=1 не гарантирует, что операция выполнена. Некоторые
опкоды (например, 65) возвращают ACK на любой запрос, игнорируя
содержимое payload. Единственный надёжный способ проверки —
запросить состояние после операции.
