# Опкоды MAX API

Все опкоды протестированы на `api.oneme.ru:443` (TCP, ver=10).
Совместимы с WebSocket (ver=11, JSON).

Подробная документация по группам опкодов:
- [Аутентификация](auth.md) — INIT, LOGIN, VERIFICATION_REQUEST, CODE_ENTER, QR, CAPTCHA
- [Сообщения](messaging.md) — MSG_SEND, MSG_DELETE, MSG_EDIT, MSG_FWD, GET_HISTORY, GET_MESSAGE, SEARCH
- [Чаты](chats.md) — GET_CHATS, CHAT_ACTION, CHAT_OPERATION, GET_STATS, IMAGE_UPLOAD_URL
- [Контакты](contacts.md) — GET_CONTACTS, CONTACTS_PRESENCE, GET_BLOCKED, GET_USERINFO, GET_COMMON_CHATS, GET_SESSIONS, GET_BANNERS
- [Файлы](files.md) — FILE_UPLOAD, GET_VIDEO_URL
- [Звонки](calls.md) — CALL_HISTORY, CALL_EDIT, CALL_TOKEN (HTTP API)
- [Пресеты](presets.md) — STICKER_SYNC, STICKER_DATA, ANIMOJI_AND_STICKER_GET, GET_PRESET_AVATARS
- [Push-уведомления](push.md) — NOTIF_TYPING, NOTIF_PRESENCE, NOTIF_ATTACH, NOTIF_MSG_DELETE, NOTIF_REACTION

## Таблица опкодов

### Системные

| Опкод | Название | cmd | Payload запроса | Документация |
|-------|----------|-----|-----------------|-------------|
| 1 | PING | 1 | `{"interactive": true}` | [push.md](push.md) |
| 5 | NAV_ANALYTICS | 1 | `{events: [{type: "NAV", event: ...}]}` | — |
| 6 | INIT | 1 | `{userAgent, deviceId}` | [auth.md](auth.md) |
| 17 | VERIFICATION_REQUEST | 1 | `{phone, type, language}` | [auth.md](auth.md) |
| 18 | CODE_ENTER | 1 | `{token, verifyCode, authTokenType}` | [auth.md](auth.md) |
| 19 | LOGIN | 1 | `{token, interactive, chatsCount, ...}` | [auth.md](auth.md) |
| 101 | CONFIG | 1 | `{}` или `{"interactive": true}` | [contacts.md](contacts.md) — конфигурация сервера |
| 224 | CAPTCHA_REQUEST | 1 | `{source, identifier}` | [auth.md](auth.md) — VK Captcha |
| 288 | QR_AUTH_REQUEST | 1 | `{}` | [auth.md](auth.md) — QR-код для входа |
| 289 | QR_AUTH_POLL | 1 | `{trackId}` | [auth.md](auth.md) — опрос статуса QR |
| 200 | SERVER_TIME | 1 | — | Получение серверного времени (unix timestamp, мс) |
| 302 | GET_BANNERS | 1 | `{bannersSync: 0}` | [contacts.md](contacts.md) |

### Сообщения

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 49 | GET_HISTORY | 1 | [messaging.md](messaging.md) |
| 51 | GET_MEDIA | 1 | [messaging.md](messaging.md) |
| 60 | MSG_SEARCH_GLOBAL | 1 | [messaging.md](messaging.md) |
| 62 | SEARCH_LIVE_STREAMS | 1 | [messaging.md](messaging.md) |
| 64 | MSG_SEND | 1 | [messaging.md](messaging.md) |
| 65 | MSG_TYPING | 1 | [messaging.md](messaging.md) |
| 66 | MSG_DELETE | 1 | [messaging.md](messaging.md) |
| 67 | MSG_EDIT | 1 | [messaging.md](messaging.md) — редактирование сообщения |
| 68 | MSG_FWD | 3* | [messaging.md](messaging.md) — deprecated, возвращает ошибку |
| 70 | FORWARD_MESSAGE | 1 | [messaging.md](messaging.md) |
| 71 | GET_MESSAGE | 1 | [messaging.md](messaging.md) |
| 73 | SEARCH_MESSAGES | 1 | [messaging.md](messaging.md) |
| 92 | CHAT_ACTIVITY | 1 | [chats.md](chats.md) |
| 178 | MSG_REACT_SET | 1 | [messaging.md](messaging.md) |
| 179 | MSG_REACT_REMOVE | 1 | [messaging.md](messaging.md) |
| 180 | GET_REACTIONS_BULK | 1 | [messaging.md](messaging.md) |
| 181 | GET_REACTIONS | 1 | [messaging.md](messaging.md) |

\* — возвращает ошибку при неполном payload (deprecated опкоды).

### Чаты и контакты

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 32 | GET_CONTACTS | 1 | [contacts.md](contacts.md) |
| 35 | CONTACTS_PRESENCE | 1 | [contacts.md](contacts.md) |
| 36 | GET_BLOCKED | 1 | [contacts.md](contacts.md) |
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
| 177 | GET_USERINFO | 1 | [contacts.md](contacts.md) |
| 198 | GET_COMMON_CHATS | 1 | [contacts.md](contacts.md) |
| 272 | GET_FOLDERS | 1 | [chats.md](chats.md) |

### Файлы, изображения, медиа

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 80 | IMAGE_UPLOAD_URL | 1 | [chats.md](chats.md) |
| 81 | IMAGE_UPLOAD_IUSMILE | 1 | [chats.md](chats.md#image_upload_iusmile-opcode-81) — iusmile.oneme.ru |
| 82 | VIDEO_UPLOAD_URL | 1 | [chats.md](chats.md) — vu.okcdn.ru |
| 87 | FILE_UPLOAD | 1 | [files.md](files.md) |
| 96 | GET_SESSIONS | 1 | [contacts.md](contacts.md) |
| 106 | GET_BOT_INFO | 3* | [contacts.md](contacts.md) — поиск бота по `botId` |

> **⚠️ GET_VIDEO_URL** (файлы): задокументирован в [files.md](files.md), но его номер opcode не установлен. Возможно `83`, но этот номер занят `CALL_LEAVE`. Требуется независимая проверка.

### Звонки (голосовые и видеозвонки)

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 69 | CALL_EDIT | 3* | [calls.md](calls.md) |
| 78 | CALL_START | 3* | [calls.md](calls.md) — требуется `conversationId` + `isVideo` |
| 79 | CALL_HISTORY | 1 | [calls.md](calls.md) — история звонковых событий в чате |
| 83 | CALL_LEAVE | 3* | [calls.md](calls.md) — требуется `{chatId, messageId}` или `{token}` |
| 84 | CALL_JOIN_LINK | 3* | [calls.md](calls.md) — CallsServiceImpl.createJoinLink |
| 158 | CALL_TOKEN | 1 | [calls.md](calls.md) |

\* — возвращает ошибку при неполном payload или для неактивных звонков.
CALL_EDIT (69) работает только для звонков, созданных через официальный
клиент. Для создания звонков используется HTTP API
`vchat.startConversation` — см. [calls.md](calls.md).

### Пресеты (стикеры, эмодзи, аватары)

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 25 | GET_PRESET_AVATARS | 1 | [presets.md](presets.md) |
| 26 | STICKER_SYNC | 1 | [presets.md](presets.md) |
| 27 | STICKER_DATA | 1 | [presets.md](presets.md) |
| 28 | ANIMOJI_AND_STICKER_GET | 1 | [presets.md](presets.md) |

### Прочие

| Опкод | Название | cmd | Документация |
|-------|----------|-----|-------------|
| 100 | VOID | 1 | Заглушка. Возвращает `cmd=1 payload=null` с любым payload. |
| 103 | VOID | 1 | Заглушка. Возвращает `cmd=1 payload={}` с любым payload. |

### Push-уведомления (cmd=0)

**Важно:** push-опкоды работают **только как уведомления** (сервер → клиент).
Их нельзя использовать как запросы (клиент → сервер) — все опкоды
диапазона 128–156 (кроме 144 и 145) возвращают ошибку
`"Unknown opcode"` при попытке отправки.

Исключения: **144** и **145** работают и как запросы (см. ниже).

| Опкод | Название | Описание | Документация |
|-------|----------|----------|-------------|
| 128 | NOTIF_MSG_EDIT | Уведомление о редактировании сообщения | [push.md](push.md) |
| 129 | NOTIF_TYPING | Уведомление о наборе текста | [push.md](push.md) |
| 130 | NOTIF_READ | Подтверждение прочтения | [push.md](push.md) |
| 131 | UNKNOWN_131 | Push-уведомление | [push.md](push.md) |
| 132 | NOTIF_PRESENCE | Изменение статуса присутствия | [push.md](push.md) |
| 133 | UNKNOWN_133 | Push-уведомление | [push.md](push.md) |
| 134 | UNKNOWN_134 | Push-уведомление | [push.md](push.md) |
| 135 | UNKNOWN_135 | Push-уведомление | [push.md](push.md) |
| 136 | NOTIF_ATTACH | Подтверждение загрузки файла | [files.md](files.md) |
| 137 | NOTIF_INCOMING_CALL | Уведомление о входящем звонке | [calls.md](calls.md) |
| 138 | UNKNOWN_138 | Push-уведомление | [push.md](push.md) |
| 139 | UNKNOWN_139 | Push-уведомление | [push.md](push.md) |
| 140 | NOTIF_MSG_DELETE_RANGE | Уведомление о массовом удалении | [push.md](push.md) |
| 141 | UNKNOWN_141 | Push-уведомление | [push.md](push.md) |
| 142 | NOTIF_MSG_DELETE | Уведомление об удалении сообщения | [push.md](push.md) |
| 143 | UNKNOWN_143 | Push-уведомление | [push.md](push.md) |
| 144 | GET_CONTACTS_V2 | **Запрос:** контакты чата по `{"chatId": int}` | [contacts.md](contacts.md) |
| 145 | PRESENCE_GET | **Запрос:** получить присутствие по `{"botId": int}` | [contacts.md](contacts.md) |
| 146-155 | UNKNOWN_146-155 | Push-уведомления (диапазон) | [push.md](push.md) |
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
