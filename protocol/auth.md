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
    "pushDeviceType": "WEBPUSH",
    "locale": "ru",
    "deviceLocale": "ru",
    "osVersion": "macOS",
    "deviceName": "Yandex Browser",
    "headerUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 YaBrowser/26.4.0.0 Safari/537.36",
    "appVersion": "26.6.17",
    "screen": "956x1470 2.0x",
    "timezone": "Europe/Moscow"
  },
  "deviceId": "<UUID>"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `userAgent.deviceType` | string | Всегда `WEB` |
| `userAgent.pushDeviceType` | string | Тип push (`WEBPUSH`) |
| `userAgent.locale` | string | Язык интерфейса (`ru`) |
| `userAgent.deviceLocale` | string | Локаль устройства (`ru`) |
| `userAgent.osVersion` | string | ОС клиента (`macOS`, `Linux`) |
| `userAgent.deviceName` | string | Название браузера (`Yandex Browser`, `Firefox`) |
| `userAgent.headerUserAgent` | string | User-Agent из HTTP-заголовка |
| `userAgent.appVersion` | string | Версия приложения (`26.6.17`) |
| `userAgent.screen` | string | Разрешение экрана и плотность (`956x1470 2.0x`) |
| `userAgent.timezone` | string | Временная зона (`Europe/Moscow`) |
| `deviceId` | string | Уникальный ID устройства (UUID) |

### Ответ

```
cmd=1 opcode=6
```

Ответ INIT может различаться в зависимости от контекста:

- **Перед LOGIN** (авторизованный пользователь) — возвращает данные сессии
- **Для неавторизованного пользователя** — возвращает конфигурацию сервера
  (те же поля, что CONFIG opcode 101): `phone-auth-enabled`, `location`,
  `lang`, `web-pwa-promo`, `reg-country-code`

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
      "participants": { "3260455": 1781688781664, "6236697": 1781697221724 },
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

---

## Альтернативная авторизация: SMS (opcode 17, 18)

MAX поддерживает авторизацию через SMS на номер телефона. Это
альтернатива токену из браузера — может быть полезна для тестирования
и автоматизации.

Процесс:
```
CAPTCHA_REQUEST (224) → капча → VERIFICATION_REQUEST (17) → SMS с кодом → CODE_ENTER (18) → access_token → LOGIN (19)
```

Перед отправкой SMS может потребоваться пройти VK Captcha (опционально,
зависит от частоты запросов). Если капча не требуется — VERIFICATION_REQUEST
можно вызывать сразу.

### 0. CAPTCHA_REQUEST (opcode 224)

Запрос VK Captcha для подтверждения, что запрос от человека.

Является частью инфраструктуры VK ID, встроенной в MAX.

**Запрос:**
```json
{
  "source": "auth",
  "identifier": "+71234567890"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `source` | string | Всегда `"auth"` |
| `identifier` | string | Номер телефона в международном формате |

**Ответ:**
```json
{
  "link": "https://id.vk.ru/not_robot_captcha?domain=web.max.ru&session_token=eyJ..."
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `link` | string | URL капчи VK ID для прохождения в браузере |

После прохождения капчи браузер получает `captchaToken`, который
передаётся в VERIFICATION_REQUEST.

### 1. VERIFICATION_REQUEST (opcode 17)

Запрос на отправку SMS с кодом подтверждения на номер телефона.

**Запрос:**
```json
{
  "phone": "+71234567890",
  "type": "START_AUTH",
  "language": "ru",
  "captchaToken": "eyJ..."
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `phone` | string | Номер телефона в международном формате |
| `type` | string | `"START_AUTH"` или `"RESEND"` |
| `language` | string | Язык SMS-сообщения (`"ru"`) |
| `captchaToken` | string | (Опционально) токен после прохождения VK Captcha |

Поле `type`:
- `"START_AUTH"` — первый запрос кода
- `"RESEND"` — повторная отправка (если код не пришёл или истёк)

**Ответ:**
```json
{
  "requestMaxDuration": 60000,
  "requestCountLeft": 10,
  "altActionDuration": 60000,
  "codeLength": 6,
  "token": "An_..."
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `token` | string | Токен для CODE_ENTER (длинная строка, начинается с `An_`) |
| `codeLength` | int | Длина кода подтверждения (6) |
| `requestMaxDuration` | int | Макс. время ожидания ввода кода (мс) |
| `requestCountLeft` | int | Сколько осталось попыток запроса кода |
| `altActionDuration` | int | Длительность альтернативного действия (мс) |

**Примечание:** После успешного запроса на указанный номер приходит
SMS с 6-значным кодом подтверждения.

### 2. CODE_ENTER (opcode 18)

Отправка кода подтверждения из SMS.

**Запрос:**
```json
{
  "token": "An_...",
  "verifyCode": "504940",
  "authTokenType": "CHECK_CODE"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `token` | string | Токен из ответа VERIFICATION_REQUEST |
| `verifyCode` | string | 6-значный код из SMS |
| `authTokenType` | string | `"CHECK_CODE"` |

**Ответ (успех):**
```json
{
  "tokenAttrs": {
    "LOGIN": {
      "token": "access_token_для_дальнейшей_работы"
    }
  }
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `tokenAttrs.LOGIN.token` | string | Токен доступа для LOGIN (opcode 19) |

**Ответ (ошибка):**
```json
{
  "localizedMessage": "Пользователь заблокирован или удалён",
  "error": "auth.blocked",
  "message": "Key: error.user.recovery.not.available"
}
```

| Код ошибки | Описание |
|------------|----------|
| `auth.blocked` | Аккаунт пользователя заблокирован |
| `auth.invalid.code` | Неверный код подтверждения |

Полученный токен можно использовать в LOGIN (opcode 19) для
полноценной авторизации.

### Полный цикл SMS-авторизации

```python
# 1. INIT (opcode 6) — обязателен перед любым запросом
ws.send(req(6, {"deviceId": device_id, "userAgent": {...}}))
ws.recv()  # INIT OK

# 2. Запрос SMS
ws.send(req(17, {
    "phone": "+71234567890",
    "type": "START_AUTH",
    "language": "ru"
}))
resp = json.loads(ws.recv())
verify_token = resp["payload"]["token"]
print(f"Токен подтверждения: {verify_token}")
# → SMS с кодом на телефон

# 3. Ввод кода (код получаете из SMS)
code = input("Введите код из SMS: ")
ws.send(req(18, {
    "token": verify_token,
    "verifyCode": code,
    "authTokenType": "CHECK_CODE"
}))
resp = json.loads(ws.recv())
access_token = resp["payload"]["tokenAttrs"]["LOGIN"]["token"]
print(f"Токен доступа: {access_token}")

# 4. LOGIN — полноценная авторизация
ws.send(req(19, {
    "token": access_token,
    "interactive": True,
    "chatsCount": 100,
    "chatsSync": 100,
}))
ws.recv()  # LOGIN OK
```

**Важно:** опкоды 17 и 18 работают через стандартное WebSocket-соединение
после INIT (opcode 6). Перед VERIFICATION_REQUEST не нужен LOGIN —
это этап, предшествующий авторизации.

## QR-авторизация (opcode 288, 289)

MAX поддерживает вход через QR-код — альтернатива SMS и токену.
Клиент запрашивает QR-код, пользователь сканирует его приложением
MAX на телефоне, после чего клиент получает токен доступа.

Процесс:
```
INIT (6) → QR_AUTH_REQUEST (288) → QR код → пользователь сканирует →
QR_AUTH_POLL (289) в цикле → CODE_ENTER (18) → LOGIN (19)
```

### 1. QR_AUTH_REQUEST (opcode 288)

Запрос на получение QR-кода для авторизации.

**Запрос:**
```json
{}
```

Пустой object. Никаких дополнительных полей не требуется.

**Ответ:**
```json
{
  "qrLink": "https://qr.max.ru/?token=eyJ...",
  "trackId": "uuid-трекера",
  "pollingInterval": 5000,
  "ttl": 119994,
  "expiresAt": 1782002818830
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `qrLink` | string | URL QR-кода для отображения |
| `trackId` | string | UUID для отслеживания статуса |
| `pollingInterval` | int | Интервал опроса статуса (мс) |
| `ttl` | int | Время жизни QR-кода (мс) |
| `expiresAt` | int | Unix timestamp истечения (мс) |

### 2. QR_AUTH_POLL (opcode 289)

Опрос статуса QR-авторизации. Вызывается в цикле с интервалом
`pollingInterval`, пока QR-код не будет отсканирован или не истечёт.

**Запрос:**
```json
{
  "trackId": "uuid-из-QR_AUTH_REQUEST"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `trackId` | string | UUID из ответа QR_AUTH_REQUEST |

**Ответ (в процессе):**
```json
{
  "status": {
    "expiresAt": 1782002818830
  }
}
```

Команда `cmd=0` (push-уведомление) — ожидание продолжается.

**Ответ (ошибка):**
```json
{
  "error": "track.not.found"
}
```

Ошибка `track.not.found` означает, что QR-код истёк или был
отсканирован ранее. В этом случае нужно запросить новый QR-код.

### 3. Завершение QR-авторизации

После успешного сканирования QR-кода сервер присылает
push-уведомление (cmd=0) с opcode 18 (CODE_ENTER), содержащее
токен доступа, аналогично SMS-флоу:

```json
{
  "cmd": 0,
  "opcode": 18,
  "payload": {
    "tokenAttrs": {
      "LOGIN": {
        "token": "access_token_для_LOGIN"
      }
    }
  }
}
```

Полученный токен используется в LOGIN (opcode 19) для полноценной
авторизации.

### Полный цикл QR-авторизации

```python
# 1. INIT
ws.send(req(6, {"deviceId": device_id, "userAgent": {...}}))
ws.recv()  # INIT OK

# 2. Запрос QR
ws.send(req(288, {}))
resp = json.loads(ws.recv())
qr_data = resp["payload"]
track_id = qr_data["trackId"]
poll_interval = qr_data["pollingInterval"]
print(f"QR URL: {qr_data['qrLink']}")

# 3. Ожидание сканирования
import time
while True:
    time.sleep(poll_interval / 1000)
    ws.send(req(289, {"trackId": track_id}))
    resp = json.loads(ws.recv())
    if resp.get("cmd") == 0 and resp.get("opcode") == 18:
        # QR отсканирован, получен токен
        access_token = resp["payload"]["tokenAttrs"]["LOGIN"]["token"]
        print(f"Токен доступа: {access_token}")
        break
    elif resp.get("cmd") == 3:
        print(f"Ошибка: {resp}")
        break

# 4. LOGIN
ws.send(req(19, {
    "token": access_token,
    "interactive": True,
    "chatsCount": 100,
    "chatsSync": 100,
}))
ws.recv()  # LOGIN OK
```

## Возможные ошибки

| Симптом | Причина |
|---------|---------|
| `cmd=3` на LOGIN | Неверный или истёкший токен |
| `cmd=3` с `error: "auth.blocked"` на CODE_ENTER (18) | Аккаунт пользователя заблокирован |
| `cmd=3` с `error: "auth.invalid.code"` на CODE_ENTER (18) | Неверный код подтверждения |
| `cmd=3` с `error: "track.not.found"` на QR_AUTH_POLL (289) | QR-код истёк или уже использован |
| Таймаут на INIT | Закончились соединения или IP заблокирован |
| `cmd=3` на любой запрос | Сессия не инициализирована (пропущен INIT/LOGIN) |
