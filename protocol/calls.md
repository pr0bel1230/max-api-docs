# Звонки: голосовые и видеозвонки

MAX поддерживает голосовые и видеозвонки между пользователями.
API звонков состоит из двух слоёв:

1. **WebSocket опкоды** — управление токенами, история, push-уведомления
2. **HTTP API** (`calls.okcdn.ru`) — создание и завершение звонков (WebRTC)

## Запись звонка в истории сообщений

В истории сообщений звонки представлены как сообщения с вложением типа `CALL`:

```json
{
  "sender": 3260455,
  "id": "115775937927062388",
  "time": 1766600615342,
  "text": "",
  "type": "USER",
  "attaches": [
    {
      "duration": 926791,
      "conversationId": "8daa66c0-04c1-4824-820b-67f92e6fd29d",
      "hangupType": "HUNGUP",
      "_type": "CALL",
      "callType": "AUDIO",
      "contactIds": [6236697]
    }
  ]
}
```

### Поля вложения CALL

| Поле | Тип | Описание |
|------|-----|----------|
| `_type` | string | Всегда `"CALL"` |
| `callType` | string | Тип звонка: `AUDIO` или `VIDEO` |
| `conversationId` | string | UUID звонка |
| `duration` | int | Длительность в миллисекундах |
| `hangupType` | string | Причина завершения (см. ниже) |
| `contactIds` | array[int] | ID того, кому звонили (всегда один ID) |

### Hangup types

| Значение | Описание |
|----------|----------|
| `HUNGUP` | Завершён (нормальное завершение) |
| `REJECTED` | Отклонён |
| `CANCELED` | Отменён (не дождались ответа) |
| `MISSED` | Пропущен (не подтверждён) |
| `BUSDY` | Занято (опечатка сервера — должно быть `BUSY`, не подтверждён) |

> **Примечание:** В 25+ записях звонков встретились только `HUNGUP`,
> `REJECTED` и `CANCELED`. `MISSED` и `BUSDY` задокументированы по данным
> раннего исследования — часть истории звонков была утеряна из-за
> каскадного удаления (см. [messaging.md#msg_delete-opcode-66](messaging.md#msg_delete-opcode-66)
> — WATERMARK BUG). На HTTP API `vchat.hangupConversation` принимает
> `reason=BUSY` как корректный параметр — вероятно, `BUSDY` был исправлен
> на `BUSY` в новых версиях сервера.

### Как создаются записи в истории

Записи CALL в истории сообщений создаются **сервером автоматически**
при звонках, совершённых через официальный клиент MAX. Звонки через
HTTP API (`vchat.startConversation`) **не создают** запись в истории —
они существуют только в инфраструктуре WebRTC.

---

## Полный цикл звонка

Реальный звонок состоит из трёх этапов, два из которых проходят через
разные API:

```
WebSocket: opcode 158 ──→ call token
                          ↓
HTTP: auth.anonymLogin ──→ session_key
                          ↓
HTTP: vchat.startConversation ──→ TURN/STUN/WebSocket endpoint
                                  │
                                  ↓
                    WebRTC медиасоединение (сигналинг через videowebrtc.okcdn.ru)
```

### 1. Запрос токена звонка (opcode 158)

Получение токена для авторизации на HTTP API звонков.

**Запрос:**
```json
{
  "opcode": 158,
  "payload": {}
}
```

Payload пустой — никаких полей не требуется.

**Ответ:**
```json
{
  "token": "$2RG9KZmzg7OoVNVtv5RDsghfvonRUpaAZugyD0VNMXuHgggaqrYyBaO62GrtwDP01t35c",
  "token_lifetime_ts": 1782490727456,
  "token_refresh_ts": 1782369767456
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `token` | string | Токен для HTTP API звонков (начинается с `$`) |
| `token_lifetime_ts` | int | Timestamp истечения токена (мс) |
| `token_refresh_ts` | int | Timestamp, когда нужно обновить токен (мс) |

### 2. Авторизация на HTTP API звонков

**Endpoint:** `https://calls.okcdn.ru/fb.do`
**Формат:** `application/x-www-form-urlencoded` (POST)
**Application key:** `CNHIJPLGDIHBABABA`

Метод `auth.anonymLogin`:

**Параметры формы:**

| Поле | Тип | Описание |
|------|-----|----------|
| `method` | string | `"auth.anonymLogin"` |
| `format` | string | `"JSON"` |
| `application_key` | string | `"CNHIJPLGDIHBABABA"` |
| `session_data` | string | JSON-строка с данными сессии (см. ниже) |

**Структура `session_data`:**
```json
{
  "auth_token": "<token из opcode 158>",
  "client_type": "SDK_JS",
  "client_version": "1.1",
  "device_id": "<UUID>",
  "version": 3
}
```

**Пример запроса:**
```python
import requests

resp = requests.post("https://calls.okcdn.ru/fb.do", data={
    "method": "auth.anonymLogin",
    "format": "JSON",
    "application_key": "CNHIJPLGDIHBABABA",
    "session_data": json.dumps({
        "auth_token": call_token,
        "client_type": "SDK_JS",
        "client_version": "1.1",
        "device_id": str(uuid.uuid4()),
        "version": 3,
    }),
})
```

**Ответ:**
```json
{
  "uid": "910111054239",
  "session_key": "-w-fl0000MtRUXBY1001U9UJGv1000000000w4pyFIoGV6oAFBM4HIMqx6pChC...",
  "session_secret_key": "3AtUcFU3JZCUXLLoAuBX",
  "api_server": "https://calls.okcdn.ru/",
  "external_user_id": "3260455"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `uid` | string | Внутренний ID сессии звонков (не совпадает с user ID) |
| `session_key` | string | Ключ сессии для последующих запросов |
| `session_secret_key` | string | Секретный ключ сессии |
| `api_server` | string | Базовый URL API сервера |
| `external_user_id` | string | Ваш user ID в MAX |

### 3. Создание звонка (startConversation)

Метод `vchat.startConversation`:

**Endpoint:** `https://calls.okcdn.ru/fb.do`
**Метод:** POST form-urlencoded

**Параметры формы:**

| Поле | Тип | Описание |
|------|-----|----------|
| `method` | string | `"vchat.startConversation"` |
| `format` | string | `"JSON"` |
| `application_key` | string | `"CNHIJPLGDIHBABABA"` |
| `conversationId` | string | UUID новой конференции (генерируется клиентом) |
| `isVideo` | string | `"true"` или `"false"` |
| `protocolVersion` | string | `"5"` |
| `payload` | string | JSON-строка: `{"is_video": false}` |
| `externalIds` | string | ID собеседника (например, `"6236697"`) |
| `session_key` | string | Ключ сессии из `auth.anonymLogin` |

**Пример запроса:**
```python
resp = requests.post("https://calls.okcdn.ru/fb.do", data={
    "method": "vchat.startConversation",
    "format": "JSON",
    "application_key": "CNHIJPLGDIHBABABA",
    "conversationId": str(uuid.uuid4()),
    "isVideo": "false",
    "protocolVersion": "5",
    "payload": json.dumps({"is_video": false}),
    "externalIds": "6236697",
    "session_key": session_key,
})
```

**Ответ:**
```json
{
  "token": "cgT8jQIasD0D7FpUgggqbk68CzBTwVh78lAh6Yzn3zk=",
  "endpoint": "wss://videowebrtc.okcdn.ru/ws2?userId=910111054239&entityType=USER&conversationId=...&token=...",
  "wt_endpoint": "https://videowebrtc.okcdn.ru:23456/wt?userId=...",
  "turn_server": {
    "urls": ["turn:155.212.205.186:19302", "turn:155.212.197.55:19302"],
    "username": "1781914758:910111054239",
    "credential": "6oQ0LJqgOPRa0NwREyrI3DXVt38="
  },
  "stun_server": {
    "urls": ["stun:155.212.205.186:19302"]
  },
  "client_type": "ONE_ME",
  "device_idx": 0,
  "id": "c1aefbb1-b61a-4ae3-89cf-8504dcb1ec30",
  "is_concurrent": false,
  "p2p_forbidden": false
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `token` | string | Токен для WebRTC сигналинга |
| `endpoint` | string | WebSocket URL для сигналинга |
| `wt_endpoint` | string | WebSocket-транспортный URL |
| `turn_server` | object | TURN сервер для медиа (urls, username, credential) |
| `stun_server` | object | STUN сервер для медиа (urls) |
| `client_type` | string | Всегда `"ONE_ME"` |
| `device_idx` | int | Индекс устройства |
| `id` | string | UUID конференции (совпадает с conversationId) |
| `is_concurrent` | bool | Флаг concurrent-звонка |
| `p2p_forbidden` | bool | Запрещён ли прямой P2P |

### 4. Завершение звонка (hangupConversation)

Метод `vchat.hangupConversation`:

**Параметры формы:**

| Поле | Тип | Описание |
|------|-----|----------|
| `method` | string | `"vchat.hangupConversation"` |
| `format` | string | `"JSON"` |
| `application_key` | string | `"CNHIJPLGDIHBABABA"` |
| `conversationId` | string | UUID конференции |
| `session_key` | string | Ключ сессии |
| `reason` | string | Причина завершения: `HUNGUP`, `REJECTED`, `CANCELED`, `BUSY` |

**Пример:**
```python
resp = requests.post("https://calls.okcdn.ru/fb.do", data={
    "method": "vchat.hangupConversation",
    "format": "JSON",
    "application_key": "CNHIJPLGDIHBABABA",
    "conversationId": conv_id,
    "session_key": session_key,
    "reason": "HUNGUP",
})
# Ответ: {} (пустой объект)
```

> **Примечание:** `reason` обязателен (`"Missing required parameter reason"`).

---

## CALL_HISTORY (opcode 79)

Получение истории звонков в чате. Работает для любого чата, где были
звонки через официальный клиент (звонки через HTTP API не создают
записи в истории).

### Запрос

```json
{
  "chatId": 7268926,
  "count": 10
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `chatId` | int | ID чата (обязательно) |
| `count` | int | Количество записей (опционально, по умолчанию — все) |

### Ответ

```json
{
  "hasMore": true,
  "history": [
    {
      "chatId": 7268926,
      "message": { "...": "полный объект сообщения с CALL attaches" },
      "chatType": "DIALOG"
    }
  ],
  "backwardMarker": 1763036952192,
  "forwardMarker": 1763042244736
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `hasMore` | bool | Есть ли ещё записи |
| `history` | array | Массив записей звонков (от newest к oldest) |
| `history[].chatId` | int | ID чата |
| `history[].message` | object | Сообщение с вложением CALL |
| `history[].chatType` | string | Тип чата (`DIALOG`, `CHAT`, `CHANNEL`) |
| `backwardMarker` | int | Маркер для пагинации назад (timestamp) |
| `forwardMarker` | int | Маркер для пагинации вперёд (timestamp) |

### Особенности

- **hasMore** = true означает, что есть более старые звонки
- **Сортировка:** от новых к старым
- **Пагинация:** backwardMarker/forwardMarker — timestamps в миллисекундах
- **contactIds** всегда содержит один ID — ID собеседника (того, кому звонили)
- **sender** сообщения — кто инициировал звонок
- `duration = 0` означает пропущенный/отклонённый звонок
- callType: `AUDIO` или `VIDEO`
- conversationId может быть как lowercase, так и uppercase UUID

---

## CALL_EDIT (opcode 69)

Управление активным звонком: отключение звука, видео, завершение.

**Важно:** Работает только для звонков, созданных через официальный
клиент (не через HTTP API). Для завершения звонков, созданных через
HTTP API, используйте `vchat.hangupConversation`.

### Запрос

```json
{
  "conversationId": "8daa66c0-04c1-4824-820b-67f92e6fd29d",
  "muteAudio": true,
  "muteVideo": false
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `conversationId` | string | UUID звонка |
| `muteAudio` | bool | Отключить микрофон |
| `muteVideo` | bool | Отключить видео |
| `muteScreenSharing` | bool | Отключить демонстрацию экрана |
| `onlyAdminCanRecord` | bool | Только админ может записывать |
| `waitingHall` | bool | Зал ожидания |
| `waitForAdmin` | bool | Ждать администратора |
| `closed` | bool | Завершить звонок |

### Внутренняя реализация

Судя по сообщению об ошибке, сервер обрабатывает через:
```
CallsServiceImpl.editCall(conversationId, userId, Mutes{muteVideo=null, muteAudio=null, ...})
```

### Ошибки

- Для завершённого звонка: `"No call <conversationId>"`
- Для звонков через HTTP API: `"No call <conversationId>"` (те же)

---

## CALL_START (opcode 78)

Инициализация нового звонка через WebSocket.

> **⚠️ ЭТОТ ОПКОД НЕ РАБОТАЕТ ДЛЯ НОВЫХ ЗВОНКОВ.**
> Реальный API звонков — через HTTP `vchat.startConversation` (см. выше).
> Opcode 78 может использоваться для джойна к существующему звонку
> или для других внутренних целей.

### Запрос

```json
{
  "isVideo": false,
  "conversationId": "uuid",
  "chatId": 7268926,
  "internalParams": ""
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `isVideo` | bool | `true` — видеозвонок, `false` — аудиозвонок |
| `conversationId` | string | UUID конференции |
| `chatId` | int | ID чата |
| `internalParams` | string | **Строка** (не объект!). Содержимое неизвестно |

### Экспериментальные результаты

- `internalParams` ожидает **строку**, не объект:
  - `""` / `"{}"` → валидация проходит, ошибка `"not.chat.participant"`
  - `{}` (объект) → `"Expected string at 91"` (proto validation error)
  - `null` / пустой массив → `"Field requirement failed: internalParams"`
- Разные значения строки (timestamp, UUID, "call") — все дают `"not.chat.participant"`
- Даже после `CHAT_SUBSCRIBE` и установки присутствия — та же ошибка
- Добавление `contactIds`, `sender` в payload — не влияет

**Вывод:** Сервер проверяет, что текущий пользователь является
участником звонка по conversationId. Без предварительно созданного
звонка (через HTTP API или официальный клиент) этот опкод всегда
возвращает ошибку. Вероятно, используется для подключения WebSocket
сессии к существующему звонку.

---

## Опкоды звонков (сводка)

| Опкод | Название | Направление | Описание |
|-------|----------|-------------|----------|
| 69 | CALL_EDIT | WS запрос | Управление звонком (mute/close) |
| 78 | CALL_START | WS запрос | Подключение к звонку (не старт!) |
| 79 | CALL_HISTORY | WS запрос | История звонков в чате |
| 137 | NOTIF_INCOMING_CALL | WS push | Уведомление о входящем звонке |
| 158 | CALL_TOKEN | WS запрос | Получение токена для HTTP API звонков |

## NOTIF_INCOMING_CALL (push, opcode 137)

Push-уведомление о входящем звонке (отправляется сервером, cmd=0).
Приходит, когда другой пользователь инициирует звонок через
официальный клиент (не подтверждён для HTTP API).

Payload содержит поле `vcp` — сжатый (LZ4 + base64) JSON с данными
сигналинга, а также `callerId` и `conversationId`.
