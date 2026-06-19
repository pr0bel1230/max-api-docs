# Аутентификация: INIT и LOGIN

Все сессии MAX начинаются с двух последовательных запросов:
**INIT (opcode 6)** → **LOGIN (opcode 19)**.

Без них ни один другой запрос работать не будет.

## INIT (opcode 6)

Инициализация сессии. Передаёт информацию об устройстве и клиенте.

### Запрос

```json
{
  "userAgent": {
    "deviceType": "WEB",
    "locale": "ru",
    "deviceLocale": "ru",
    "osVersion": "Linux",
    "deviceName": "Firefox",
    "headerUserAgent": "Mozilla/5.0 ...",
    "appVersion": "25.11.1",
    "screen": "1080x1920 1.0x",
    "timezone": "Asia/Yekaterinburg"
  },
  "deviceId": "<device_id>"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `userAgent.deviceType` | string | Всегда `WEB` |
| `userAgent.locale` | string | Язык интерфейса (`ru`) |
| `userAgent.deviceLocale` | string | Локаль устройства (`ru`) |
| `userAgent.osVersion` | string | ОС клиента (`Linux`) |
| `userAgent.deviceName` | string | Название браузера (`Firefox`) |
| `userAgent.headerUserAgent` | string | User-Agent из HTTP-заголовка |
| `userAgent.appVersion` | string | Версия приложения (25.11.1) |
| `userAgent.screen` | string | Разрешение экрана и плотность (`1080x1920 1.0x`) |
| `userAgent.timezone` | string | Временная зона (`Asia/Yekaterinburg`) |
| `deviceId` | string | Уникальный ID устройства |

### Ответ

```
cmd=1 opcode=6
```

Ответ содержит ведущие ints (`-16, 75`) и объект с данными сессии.
Payload невелик — несколько десятков байт.

### Особенности TCP

При использовании TCP (ver=10) ответ INIT содержит ведущие ints
перед msgpack-объектом. Подробнее в [tcp-protocol.md](tcp-protocol.md).

### Получение deviceId

`deviceId` можно извлечь из INIT-запроса веб-клиента через DevTools:
1. Открыть [web.max.ru](https://web.max.ru)
2. F12 → Network → фильтр `WS`
3. Найти первое сообщение WebSocket (opcode 6)
4. Скопировать `payload.deviceId`

## LOGIN (opcode 19)

Авторизация по токену доступа.

### Запрос

```json
{
  "interactive": true,
  "token": "<access_token>",
  "chatsCount": 100,
  "chatsSync": 100,
  "contactsSync": 0,
  "presenceSync": 0,
  "draftsSync": 0
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `token` | string | Токен сессии (обязательно) |
| `interactive` | bool | Флаг интерактивной сессии |
| `chatsCount` | int | Сколько чатов загрузить |
| `chatsSync` | int | Сколько чатов синхронизировать |
| `contactsSync` | int | 0 — не синхронизировать контакты |
| `presenceSync` | int | 0 — не синхронизировать статусы |
| `draftsSync` | int | 0 — не синхронизировать черновики |

### Ответ

```
cmd=1 opcode=19
```

Payload содержит полные данные пользователя:

```json
{
  "profile": {
    "contact": {
      "id": 3260455,
      "names": [{"name": "Имя Фамилия", "type": "FULL_NAME"}],
      "about": "статус",
      "phones": [{"number": "+71234567890", "type": "MOBILE"}],
      "picture": { "url": "https://...", "base": "..." }
    },
    "settings": { ... }
  },
  "chats": [
    {
      "id": 7268926,
      "type": "DIALOG",
      "title": "Имя собеседника или название",
      "lastMessage": { "text": "...", ... },
      "newMessages": 0,
      "members": [ ... ],
      "picture": { ... }
    }
  ],
  "users": [
    { "id": 3260455, ... }
  ],
  "seq1": 0,
  "seq2": 0
}
```

| Поле ответа | Описание |
|-------------|----------|
| `profile` | Данные текущего пользователя |
| `chats` | Список чатов (по `chatsCount`) |
| `users` | Участники чатов |

### Получение токена

Токен доступа — временный (живёт, пока открыта веб-версия):

1. Открыть [web.max.ru](https://web.max.ru)
2. F12 → Network → фильтр `WS`
3. Найти сообщение с `opcode: 19` (LOGIN)
4. Скопировать `payload.token` — длинная строка

Токен можно также получить из заголовков XHR-запросов к API.

## Полный цикл (TCP)

```python
# INIT
send_frame(sock, 10, 0, 1, 6, {
    "userAgent": { "deviceType": "WEB", ... },
    "deviceId": "<device_id>"
})
# -> cmd=1 opcode=6

# LOGIN
send_frame(sock, 10, 0, 2, 19, {
    "token": "<access_token>",
    "interactive": True,
    "chatsCount": 100,
    "chatsSync": 100,
    ...
})
# -> cmd=1 opcode=19, payload = profile + chats
```

## Полный цикл (WebSocket)

```python
# INIT
ws.send(json.dumps({
    "ver": 11, "cmd": 0, "seq": 1, "opcode": 6,
    "payload": { "userAgent": {...}, "deviceId": "<device_id>" }
}))

# LOGIN
ws.send(json.dumps({
    "ver": 11, "cmd": 0, "seq": 2, "opcode": 19,
    "payload": { "token": "<access_token>", "interactive": True, ... }
}))

# Ждём ответ LOGIN
for _ in range(10):
    resp = json.loads(ws.recv())
    if resp.get("cmd") == 1 and resp.get("opcode") == 19:
        print("LOGIN OK")
        break
```

## Seq и ответы

- `seq` в TCP — 2 байта (`seq % 256`), в WebSocket — любое число
- Ответы могут приходить вперемешку с push-уведомлениями (cmd=0)
- Сопоставлять ответ с запросом нужно по `seq`

## Возможные ошибки

| Симптом | Причина |
|---------|---------|
| `cmd=3` на LOGIN | Неверный или истёкший токен |
| Таймаут на INIT | Закончились соединения или IP заблокирован |
| `cmd=3` на любой запрос | Сессия не инициализирована (пропущен INIT/LOGIN) |
