# Опкоды MAX API

Все опкоды протестированы на `api.oneme.ru:443` (TCP, ver=10).
Совместимы с WebSocket (ver=11, JSON).

Подробная документация по группам опкодов:
- [Аутентификация](auth.md) — INIT, LOGIN
- [Сообщения](messaging.md) — MSG_SEND, MSG_DELETE, GET_HISTORY, GET_MESSAGE, SEARCH
- [Чаты](chats.md) — GET_CHATS, CHAT_ACTION, CHAT_OPERATION, GET_STATS, IMAGE_UPLOAD_URL
- [Контакты](contacts.md) — GET_CONTACTS, профиль
- [Файлы](files.md) — FILE_UPLOAD, прикрепление файлов
- [Звонки](calls.md) — CALL_HISTORY, CALL_EDIT, CALL_START
- [Пресеты](presets.md) — GET_PRESET_AVATARS, GET_PRESETS
- [Push-уведомления](push.md) — NOTIF_PRESENCE, NOTIF_ATTACH

## Таблица опкодов

### Системные

| Опкод | Название | cmd | Payload запроса | Документация |
|-------|----------|-----|-----------------|-------------|
| 1 | PING | 1 | `{"interactive": true}` | [push.md](push.md) |
| 5 | NAV_ANALYTICS | 1 | `{events: [{type: "NAV", event: ...}]}` | — |
| 6 | INIT | 1 | `{userAgent, deviceId}` | [auth.md](auth.md) |
| 19 | LOGIN | 1 | `{token, interactive, chatsCount, ...}` | [auth.md](auth.md) |
| 200 | SERVER_TIME | 1 | — | — |
| 302 | GET_BANNERS | 1 | `{bannersSync: 0}` | — |

### Сообщения

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 49 | GET_HISTORY | 1 | [messaging.md](messaging.md) |
| 51 | GET_MEDIA | 1 | [messaging.md](messaging.md) |
| 64 | MSG_SEND | 1 | [messaging.md](messaging.md) |
| 65 | MSG_TYPING | 1 | [messaging.md](messaging.md) |
| 66 | MSG_DELETE | 1 | [messaging.md](messaging.md) |
| 67 | MSG_EDIT | 1 | [messaging.md](messaging.md) |
| 68 | MSG_FWD | 3 | — |
| 70 | FORWARD_MESSAGE | 1 | [messaging.md](messaging.md) |
| 71 | GET_MESSAGE | 1 | [messaging.md](messaging.md) |
| 73 | SEARCH_MESSAGES | 1 | [messaging.md](messaging.md) |
| 92 | CHAT_ACTIVITY | 1 | [chats.md](chats.md) |
| 178 | MSG_REACT_SET | 1 | [messaging.md](messaging.md) |
| 179 | MSG_REACT_REMOVE | 1 | [messaging.md](messaging.md) |
| 180 | GET_REACTIONS_BULK | 1 | [messaging.md](messaging.md) |
| 181 | GET_REACTIONS | 1 | [messaging.md](messaging.md) |

\* — на момент исследования. Возможно, требуется другой payload.

### Чаты и контакты

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 32 | GET_CONTACTS | 1 | [contacts.md](contacts.md) |
| 35 | CONTACTS_PRESENCE | 1 | — |
| 36 | GET_BLOCKED | 1 | — |
| 48 | GET_CHATS_BULK | 1 | [chats.md](chats.md) |
| 50 | CHAT_READ | 1 | [chats.md](chats.md) |
| 53 | GET_CHATS | 1 | [chats.md](chats.md) |
| 55 | VOID | 1 | [chats.md](chats.md) |
| 61 | GET_CHAT_INFO | 1 | [chats.md](chats.md) |
| 72 | CHAT_ACTION | 1 | [chats.md](chats.md) |
| 74 | GET_STATS | 1 | [chats.md](chats.md) |
| 75 | CHAT_SUBSCRIBE | 1 | [chats.md](chats.md) |
| 77 | CHAT_OPERATION | 1 | [chats.md](chats.md) |
| 86 | CHAT_SHOW | 1 | [chats.md](chats.md) |
| 177 | GET_USERINFO | 1 | — |
| 198 | GET_COMMON_CHATS | 1 | — |
| 272 | GET_FOLDERS | 1 | [chats.md](chats.md) |

### Файлы, изображения, медиа

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 80 | IMAGE_UPLOAD_URL | 1 | [chats.md](chats.md) |
| 81 | IMAGE_UPLOAD_IUSMILE | 1 | [chats.md](chats.md) |
| 83 | GET_VIDEO_URL | 1 | — |
| 87 | FILE_UPLOAD | 1 | [files.md](files.md) |
| 96 | GET_SESSIONS | 1 | — |

### Звонки (голосовые и видеозвонки)

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 69 | CALL_EDIT | 3* | [calls.md](calls.md) |
| 78 | CALL_START | 3* | [calls.md](calls.md) |
| 79 | CALL_HISTORY | 1 | [calls.md](calls.md) |

\* — возвращает ошибку валидации при неполном payload.

### Пресеты (стикеры, эмодзи, аватары)

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 25 | GET_PRESET_AVATARS | 1 | [presets.md](presets.md) |
| 26 | GET_PRESETS | 1 | [presets.md](presets.md) |
| 27 | GET_STICKER_SETS | 1 | — |
| 28 | GET_ANIMOJI | 1 | — |

### Прочие

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 100 | VOID | 1 | — |
| 103 | VOID | 1 | — |
| 200 | SERVER_TIME | 1 | — |

### Push-уведомления (cmd=0)

| Опкод | Название | Описание | Документация |
|-------|----------|----------|-------------|
| 128 | NOTIF_MSG_EDIT | Уведомление о редактировании сообщения | [push.md](push.md) |
| 129 | NOTIF_TYPING | Уведомление о наборе текста | [push.md](push.md) |
| 132 | NOTIF_PRESENCE | Изменение статуса присутствия | [push.md](push.md) |
| 136 | NOTIF_ATTACH | Подтверждение загрузки файла | [files.md](files.md) |
| 140 | NOTIF_MSG_DELETE_RANGE | Уведомление о массовом удалении | [push.md](push.md) |
| 142 | NOTIF_MSG_DELETE | Уведомление об удалении сообщения | [push.md](push.md) |
| 156 | NOTIF_REACTION | Уведомление о реакции на сообщение | [messaging.md](messaging.md) |

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

**⚠️ ВАЖНО: MSG_DELETE (66) с `forMe=false` может вызвать каскадное
удаление** — если перед ним был вызван CHAT_ACTIVITY (92), сервер
удаляет **все** сообщения до установленного водяного знака, а не
только указанные в `messageIds`. Подробнее в
[messaging.md#msg_delete-opcode-66](messaging.md#msg_delete-opcode-66).
**Никогда не используйте MSG_DELETE с `forMe=false` на реальных чатах.**
