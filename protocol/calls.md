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
| `conversationId` | string | UUID звонка (может быть как lowercase, так и UPPERCASE) |
| `duration` | int | Длительность в миллисекундах (предп.), 0 = пропущен/отклонён. |
| | | Наблюдаемые: 428996 (7 мин), 926791 (15 мин), 1317377 (22 мин) — |
| | | что соответствует ms→min, а не секундам |
| `hangupType` | string | Причина завершения (см. ниже) |
| `contactIds` | array[int] | ID того, кому звонили (всегда один ID) |
| `sender` | int | Кто инициировал звонок (из message.sender, не в attaches) |

### Hangup types

| Значение | Описание |
|----------|----------|
| `HUNGUP` | Завершён (нормальное завершение) |
| `REJECTED` | Отклонён |
| `CANCELED` | Отменён (не дождались ответа) |
| `MISSED` | Пропущен (не подтверждён) |
| `BUSDY` | Занято (опечатка сервера — должно быть `BUSY`, не подтверждён) |

> **Примечание:** В 50+ записях звонков встретились только `HUNGUP`,
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
они существуют только в инфраструктуре WebRTC и видны через
`vchat.getHistory`.

После завершения звонка сервер присылает push **opcode 128 (NOTIF_MSG_EDIT)**
с CALL-вложением. Без вызова MSG_SEND — сервер сам создаёт сообщение.

**Пример из HAR (реальный звонок, hangupType: HUNGUP):**
```json
{
  "opcode": 128,
  "payload": {
    "chatId": 309052361,
    "message": {
      "sender": 307889134,
      "id": "116778126815396519",
      "time": 1781892804190,
      "text": "",
      "type": "USER",
      "attaches": [{
        "duration": 34122,
        "conversationId": "55B0077C-8944-43B6-9258-F7BBB26AEF10",
        "hangupType": "HUNGUP",
        "_type": "CALL",
        "callType": "AUDIO",
        "contactIds": [307889134]
      }]
    }
  }
}
```

CALL-сообщение создаётся сервером **в момент hangup**, а не в момент
старта звонка. Поэтому `duration` известна точно.

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
  "token": "$<call_token>",
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
  "token": "<signaling_token>",
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
  "is_concurrent": false,
  "p2p_forbidden": false
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `token` | string | Токен для WebRTC сигналинга |
| `endpoint` | string | WebSocket URL для сигналинга |
| `wt_endpoint` | string | WebSocket-транспортный URL (HTTPS, не WSS) |
| `turn_server` | object | TURN сервер для медиа (urls, username, credential) |
| `stun_server` | object | STUN сервер для медиа (urls) |
| `client_type` | string | Всегда `"ONE_ME"` |
| `device_idx` | int | Индекс устройства |
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

### 5. Вспомогательные HTTP API методы

#### system.getInfo

Получение информации о сессии звонков:

**Запрос:**
```
POST https://calls.okcdn.ru/fb.do
  method=system.getInfo
  format=JSON
  application_key=CNHIJPLGDIHBABABA
  session_key=<key>
```

**Ответ:**
```json
{
  "uid": 910111054239,
  "scopes": ["calls", "history", "audio", "video"]
}
```

#### vchat.clientStats

Отправка статистики клиента. Вызывается периодически во время звонка
и при завершении. В HAR оба файла отправляют этот метод для мониторинга
качества:

```json
{
  "items": [
    {"name": "websocket_connected", "value": 640, "call_topology": "D", ...},
    {"name": "signaling_connected", "value": 658, ...},
    {"name": "codec_usage", "codec_implementation": "audio/opus/encoder", "value": 0,
     "string_value": "dred=100;minbitrate=16000;minptime=10;usedtx=1;useinbandfec=0", ...},
    {"name": "call_finish", "reason": "hangup", ...},
    ...
  ]
}
```

Параметры запроса:

| Поле | Тип | Описание |
|------|-----|----------|
| `data` | string | JSON с полями `items`, `app_version`, `sdk_type`, `sdk_version`, `version` |
| `method` | string | `"vchat.clientStats"` |
| `session_key` | string | Ключ сессии |

Поля `call_finish`: `reason` (`"hangup"`), `vcid` (UUID конференции),
`timestamp`. Поля `codec_usage`: `codec_implementation`
(`"audio/opus/encoder"`), `string_value` (параметры кодека).

---

## WebRTC Signaling (videowebrtc.okcdn.ru)

Сигналинг — WebSocket соединение для обмена WebRTC SDP/ICE между участниками
звонка. Использует отдельный сервер `videowebrtc.okcdn.ru`.

### Протокол сообщений

Все сообщения — JSON. Сервер присылает `notification`, клиент отправляет `command`:

**Уведомления (от сервера):**

| `notification` | Описание |
|----------------|----------|
| `connection` | ServerHello — первое сообщение после подключения |
| `settings-update` | Настройки камеры/экрана/сети |
| `registered-peer` | Другой участник зарегистрировал свой WebRTC peer |
| `transmitted-data` | SDP offer/answer или ICE candidates |
| `media-settings-changed` | Другой участник изменил настройки медиа |
| `feature-set-changed` | Обновление фич конференции (`RECORD`, `ADD_PARTICIPANT`) |
| `features-per-role-changed` | Обновление фич по ролям |
| `hungup` | Участник завершил звонок |
| `closed-conversation` | Конференция закрыта |

**Команды (от клиента):**

| `command` | Описание |
|-----------|----------|
| `accept-call` | Принять входящий звонок |
| `get-rooms` | Получить комнаты конференции |
| `change-media-settings` | Изменить настройки микрофона/камеры |
| `transmit-data` | Отправить SDP answer или ICE candidates |
| `custom-data` | Отправить статистику качества сети |
| `update-display-layout` | Обновить расположение видео в UI |

### URL параметры

**Входящий звонок (accept):**
```
wss://videowebrtc.okcdn.ru/ws2
  ?userId=910111054239
  &entityType=USER
  &deviceIdx=0
  &conversationId=<UUID>
  &token=<token>
  &platform=WEB
  &appVersion=1.1
  &version=5
  &device=browser
  &capabilities=2A03F
  &clientType=one_me
  &tgt=accept
```

**Исходящий звонок (start):** (из HTTP API startConversation)
```
wss://videowebrtc.okcdn.ru/ws2
  ?userId=910111054239
  &entityType=USER
  &conversationId=<UUID>
  &token=<token>
```

Параметры:

| Параметр | Описание |
|----------|----------|
| `userId` | Внутренний signaling ID (из auth.anonymLogin.uid) |
| `entityType=USER` | Всегда USER |
| `deviceIdx` | 0 (для входящего; отсутствует или другой для исходящего) |
| `conversationId` | UUID конференции |
| `token` | Токен доступа |
| `platform=WEB` | Платформа |
| `appVersion` | Версия (1.1 в HAR, может быть 25.11.1) |
| `version` | Версия протокола (5 в HAR, может быть 2) |
| `capabilities` | WebRTC capabilities (2A03F) |
| `clientType` | **`one_me`** — нижний регистр! (для входящего) |
| `tgt` | **`accept`** — для принимающего звонок |

### ServerHello (connection)

Первое сообщение после подключения:

```json
{
  "stamp": 1781890375933000000,
  "peerId": {
    "id": 44831014303
  },
  "endpoint": "wss://videowebrtc.okcdn.ru/ws2?conversationId=...&peerId=...&token=...&userId=...&entityType=USER",
  "conversationParams": {
    "turn": {
      "urls": [
        "turn:155.212.205.187:19302",
        "turn:155.212.199.143:19302"
      ],
      "username": "1781919175:910111054239",
      "credential": "WEDLONNrpvjqsKyU6ZBcMtqQ8LQ="
    },
    "stun": {
      "urls": [
        "stun:155.212.205.187:19302"
      ]
    },
    "serverTime": 1781890375933,
    "activityTimeout": 120000
  },
  "conversation": {
    "id": "07A51A28-346C-46B4-BADE-1518ACD91036",
    "state": "ACTIVE",
    "topology": "DIRECT",
    "participants": [
      {
        "externalId": {
          "type": "ONE_ME",
          "id": "3260455"
        },
        "state": "CALLED",
        "mediaSettings": {
          "isAudioEnabled": true
        },
        "id": 910111054239
      },
      {
        "externalId": {
          "type": "ONE_ME",
          "id": "307889134"
        },
        "state": "ACCEPTED",
        "roles": ["CREATOR"],
        "mediaSettings": {
          "isAudioEnabled": true
        },
        "permissions": [
          "MUTE_PARTICIPANTS",
          "REMOVE_JOIN_LINK"
        ],
        "id": 1125899996294935
      }
    ],
    "participantsLimit": 1500,
    "features": ["RECORD"],
    "featuresPerRole": {},
    "options": ["FEEDBACK"],
    "clientType": "ONE_ME",
    "handCount": 0
  },
  "isConcurrent": false,
  "mediaModifiers": {
    "denoise": true,
    "denoiseAnn": true
  },
  "notification": "connection",
  "type": "notification"
}
```

**Важно про участников:**
- `state: "CALLED"` = тот, кому звонят (вы)
- `state: "ACCEPTED" + roles: ["CREATOR"]` = звонящий

**Поля ServerHello:**

| Поле | Тип | Описание |
|------|-----|----------|
| `stamp` | long | Timestamp наносекунды |
| `type` | string | `"notification"` |
| `peerId.id` | long | ID ассоциированного WebSocket пира |
| `endpoint` | string | WebSocket URL с peerId |
| `conversationParams.turn` | object | TURN серверы (urls, username, credential) |
| `conversationParams.stun` | object | STUN серверы (urls) |
| `conversationParams.serverTime` | long | Серверное время (мс) |
| `conversationParams.activityTimeout` | int | Таймаут активности (мс) |
| `conversation.state` | string | `"ACTIVE"`, `"ENDED"` |
| `conversation.topology` | string | `"DIRECT"` (P2P, без MCU/SFU) |
| `conversation.participants` | array | Участники звонка |
| `conversation.participantsLimit` | int | Лимит участников (1500) |
| `conversation.features` | array | `["RECORD"]`, после accept `["RECORD","ADD_PARTICIPANT"]` |
| `conversation.clientType` | string | `"ONE_ME"` |
| `mediaModifiers` | object | `{denoise, denoiseAnn}` |

### Settings Update

Сразу после ServerHello приходит настройки конференции:

```json
{
  "stamp": 1781890375933000000,
  "camera": {
    "maxDimension": 1280,
    "maxBitrateK": 2000,
    "degradationPreference": "maintain-framerate"
  },
  "screenSharing": {
    "maxDimension": 1920,
    "maxBitrateK": 3000,
    "maxFramerate": 30,
    "degradationPreference": "maintain-resolution"
  },
  "settings": {
    "badNet": {
      "rtt": 1000,
      "loss": 7
    },
    "goodNet": {
      "rtt": 600,
      "loss": 0.5
    }
  },
  "notification": "settings-update",
  "type": "notification"
}
```

### Registered Peer

Другой участник зарегистрировал свой WebRTC peer:

```json
{
  "stamp": 1781890376163000000,
  "peerId": {
    "id": -2411862425106941082,
    "type": "WEB_TRANSPORT"
  },
  "platform": "IOS",
  "clientType": "ONE_ME",
  "notification": "registered-peer",
  "participantType": "USER",
  "participantId": 1125899996294935,
  "type": "notification"
}
```

### TransmitData — SDP offer (от звонящего)

```json
{
  "stamp": 1781890376273000000,
  "peerId": {
    "id": -2411862425106941082,
    "type": "WEB_TRANSPORT"
  },
  "data": {
    "sdp": {
      "type": "offer",
      "sdp": "v=0\r\no=- 1541281659360338836 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE 0 1\r\n..."
    }
  },
  "notification": "transmitted-data",
  "type": "notification"
}
```

### TransmitData — ICE candidates

```json
{
  "stamp": 1781890376273000001,
  "peerId": {
    "id": -2411862425106941082,
    "type": "WEB_TRANSPORT"
  },
  "data": {
    "candidate": {
      "candidate": "candidate:468136283 1 udp 658217562 155.212.193.195 43210 typ host generation 0 ufrag EiJd4rKuwfkccfz network-id 1 network-cost 10",
      "sdpMid": "0",
      "usernameFragment": "EiJd4rKuwfkccfz",
      "sdpMLineIndex": 0
    }
  },
  "notification": "transmitted-data",
  "participantType": "USER",
  "participantId": 1125899996294935,
  "type": "notification"
}
```

### Hungup

Уведомление о том, что участник завершил звонок. Приходит, когда
**другой** участник (не вы) завершает звонок. После этого сервер
закрывает конференцию (`closed-conversation`).

#### Наблюдаемые причины:

| `reason` | Описание |
|----------|----------|
| `CANCELED` | Звонящий отменил (недозвон/не ответили) |
| `HUNGUP` | Нормальное завершение (положили трубку) |

```json
{
  "stamp": 1781892804166000000,
  "markers": {
    "SIDE": {"rank": 258},
    "GRID": {"rank": 2, "ts": 1781892764924}
  },
  "deviceCount": 0,
  "peerId": {"id": 2481725040034464360, "type": "WEB_TRANSPORT"},
  "reason": "HUNGUP",
  "traceId": "uyLi0PYNMkIveN9D",
  "notification": "hungup",
  "participantType": "USER",
  "participantId": 1125899996294935,
  "type": "notification"
}
```

**Поля маркеров:**

| Поле | Описание |
|------|----------|
| `SIDE.rank` | Порядковый номер звонка в сессии WebSocket (инкремент) |
| `GRID.rank` | Версия layout-сетки участников |
| `GRID.ts` | Timestamp создания/изменения grid (мс) |

`traceId` — уникальный ID для трейсинга звонка (логирование на сервере).

### Closed Conversation

```json
{
  "stamp": 1781890384926000001,
  "reason": "CANCELED",
  "notification": "closed-conversation",
  "type": "notification"
}
```

### Keep-alive

Сервер регулярно присылает `"ping"` (raw string, не JSON).
Клиент должен отвечать `"pong"` (raw string).

---
    
## Принятие входящего звонка (accept-call)
    
После получения **ServerHello (connection)**, принимающая сторона
должна подтвердить принятие звонка.
    
### accept-call команда
    
Клиент отправляет команду принятия звонка:
    
```json
{
  "command": "accept-call",
  "sequence": 1,
  "mediaSettings": {
    "isAudioEnabled": true,
    "isVideoEnabled": false,
    "isScreenSharingEnabled": false,
    "isFastScreenSharingEnabled": false,
    "isAudioSharingEnabled": false,
    "isAnimojiEnabled": false
  }
}
```
    
Сервер отвечает:
```json
{
  "stamp": 0,
  "sequence": 1,
  "participantIds": [1125899996294935],
  "participantTypes": ["USER"],
  "participantDeviceIdxs": [0],
  "response": "accept-call",
  "type": "response"
}
```
    
| Поле | Тип | Описание |
|------|-----|----------|
| `command` | string | `"accept-call"` |
| `sequence` | int | Порядковый номер (инкремент) |
| `mediaSettings.isAudioEnabled` | bool | Включён ли микрофон |
| `mediaSettings.isVideoEnabled` | bool | Включена ли камера |
| `mediaSettings.isScreenSharingEnabled` | bool | Демонстрация экрана |
| `mediaSettings.isAnimojiEnabled` | bool | Animoji |
    
### get-rooms
    
После accept-call клиент может запросить список комнат (возвращает пустой ответ):
    
```json
{"command": "get-rooms", "sequence": 2, "withParticipants": false}
→ {"stamp": 0, "sequence": 2, "response": "get-rooms", "type": "response"}
```
    
### change-media-settings
    
Обновление настроек микрофона/камеры:
    
```json
{
  "command": "change-media-settings",
  "sequence": 3,
  "mediaSettings": {
    "isAudioEnabled": true,
    "isVideoEnabled": false,
    "isScreenSharingEnabled": false,
    "isFastScreenSharingEnabled": false,
    "isAudioSharingEnabled": false,
    "isAnimojiEnabled": false
  }
}
→ {"stamp": 0, "sequence": 3, "response": "change-media-settings", "type": "response"}
```
    
### SDP Answer
    
После confirmation клиент отправляет свой SDP (WebRTC answer) обратно
через signaling WebSocket. Сообщение содержит поле `sdp` (без обёртки
`transmitted-data`):
    
```json
{
  "sdp": {
    "type": "answer",
    "sdp": "v=0\r\no=- 4863679689994311007 2 IN IP4 127.0.0.1\r\n..."
  }
}
```
    
Ответ подтверждается через:
```json
{"stamp": 0, "sequence": 4, "response": "transmit-data", "type": "response"}
```
    
### ICE Candidates
    
Каждый ICE candidate отправляется отдельно и подтверждается RESPONSE:
    
```json
{
  "candidate": {
    "candidate": "candidate:2864754332 1 udp 2122260223 192.168.0.108 58394 typ host generation 0 ufrag U7bO network-id 1 network-cost 10",
    "sdpMid": "0",
    "sdpMLineIndex": 0,
    "usernameFragment": "U7bO"
  }
}
→ {"stamp": 0, "sequence": N, "response": "transmit-data", "type": "response"}
```
    
**Особенности:**
- Каждый candidate — отдельное сообщение (не батч)
- Каждый candidate подтверждается RESPONSE с уникальным `sequence`
- `usernameFragment` должен совпадать с ICE ufrag из SDP answer
- Порядок отправки: host → srflx → relay → tcp

Типы candidates, наблюдаемые в real-звонке:
- `host` — локальный IP (192.168.x.x, 198.18.x.x)
- `srflx` — внешний IP (NAT)
- `relay` — TURN релей (155.212.x.x)
- `tcp` — TCP fallback
    
### media-settings-changed — уведомление от другого участника

Когда **другой** участник звонка меняет настройки микрофона/камеры,
сервер присылает уведомление:

```json
{
  "stamp": 1781892790836000000,
  "peerId": {"id": 2481725040034464360, "type": "WEB_TRANSPORT"},
  "mediaSettings": {
    "isAudioEnabled": true,
    "isVideoEnabled": true
  },
  "notification": "media-settings-changed",
  "participantType": "USER",
  "participantId": 1125899996294935,
  "type": "notification"
}
```

**Последовательность из real-звонка (audio→video→audio):**
1. `mediaSettings: {}` — пустой объект (возможно, начальное состояние)
2. `isAudioEnabled: true` — включил микрофон
3. `isAudioEnabled: true, isVideoEnabled: true` — включил камеру
4. `isAudioEnabled: true` — выключил камеру

Пустой `mediaSettings: {}` означает, что участник только подключился
и ещё не выбрал настройки (или все опции выключены).

### update-display-layout — команда расположения видео

После установки медиасоединения клиент может отправить команду
управления расположением видео в UI:

```json
{
  "command": "update-display-layout",
  "sequence": 25,
  "layouts": {
    "u1125899996294935:sCAMERA": "ss"
  }
}
```

Формат: `"u<participantId>:<source>"` → `"<layout>"`.
- `sCAMERA` — источник видео (камера)
- `ss` — layout-режим (вероятно, "screen share" или "single speaker")

### feature-set-changed
    
После подключения всех участников сервер обновляет фичи конференции:
    
```json
{
  "stamp": 1781893455474000001,
  "features": ["RECORD", "ADD_PARTICIPANT"],
  "notification": "feature-set-changed",
  "type": "notification"
}
```
    
### custom-data — статистика качества сети

Клиент периодически отправляет отчёт о качестве сети через команду
`custom-data` с типом `bad-net`:

```json
{
  "command": "custom-data",
  "sequence": 19,
  "data": {
    "sdk": {
      "type": "bad-net",
      "rtt": 7,
      "loss": 0
    }
  },
  "participantId": null
}
→ {"stamp": 0, "sequence": 19, "response": "custom-data", "type": "response"}
```

**Наблюдаемые интервалы (из real-звонка):**
| seq | Прошло (мс) | RTT | Loss | Событие |
|-----|-------------|-----|------|---------|
| 19 | 0 | 7 | 0 | После accept-call |
| 24 | ~32800 | 23.989 | 0.507 | Через ~33 сек |

`participantId: null` — статистика для всей конференции, а не для
конкретного участника.
    
### Подключение к активному звонку
    
Проверено экспериментально: можно подключиться к **уже идущему** звонку
(conversation state = `ACTIVE`). Сервер не кикает дополнительное
подключение от того же участника — отдаёт ServerHello с полными данными
(participants, TURN/STUN, peerId).

Это позволяет, например, программно наблюдать активный звонок или
потенциально присоединиться к нему через WebRTC.

**Что видно при подключении к ACTIVE звонку (со своим токеном):**
```json
{
  "peerId": {"id": 44838083999},
  "conversation": {
    "state": "ACTIVE",
    "topology": "DIRECT",
    "participants": [
      {"externalId": {"id": "3260455"}, "state": "ACCEPTED"},
      {"externalId": {"id": "307889134"}, "state": "ACCEPTED", "roles": ["CREATOR"]}
    ],
    "participantsLimit": 1500
  },
  "conversationParams": {
    "turn": {"urls": ["turn:155.212.205.104:19302", ...]},
    "stun": {"urls": ["stun:155.212.205.104:19302"]},
    "activityTimeout": 120000
  }
}
```

> **Важно:** это подключение к **своему** звонку со своим signaling токеном.
> VCP-токен из push 137 выдаётся конкретному участнику звонка (через
> `auth.anonymLogin`). Сервер проверяет связку `token + userId + conversationId`.
> Подключение к чужому звонку требует чужого VCP — его нельзя получить
> легально. Подробнее о модели безопасности см.
> [calls-security.md](calls-security.md).

### Причины завершения звонка (signaling)

Подтверждённые в HAR:

| `reason` | Тип звонка | Описание |
|----------|------------|----------|
| `CANCELED` | Неотвеченные (4 звонка) | Звонящий отменил, не дождавшись ответа |
| `HUNGUP` | Принятые (3 звонка) | Нормальное завершение, положили трубку |

`TIMEOUT` и `REJECTED` не встречены в HAR (ожидаются для таймаута
и отклонённых звонков соответственно).

---

## NOTIF_INCOMING_CALL (push, opcode 137) — подтверждено из HAR

Push-уведомление о входящем звонке. Сервер отправляет (cmd=0), когда
другой пользователь звонит через официальный клиент.

```json
{
  "ver": 11,
  "cmd": 0,
  "opcode": 137,
  "payload": {
    "vcp": "<protobuf+b64 signaling params>",
    "chatId": 0,
    "conversationId": "07A51A28-346C-46B4-BADE-1518ACD91036",
    "callerId": 307889134,
    "type": "AUDIO",
    "isContact": true
  }
}
```

### Поля payload:

| Поле | Тип | Описание |
|------|-----|----------|
| `vcp` | string | Protobuf-запакованный JSON в base64 (см. ниже) |
| `chatId` | int | Всегда 0 (используется conversationId) |
| `conversationId` | string | UUID signaling сессии |
| `callerId` | int | MAX user ID звонящего |
| `type` | string | `"AUDIO"` или `"VIDEO"` |
| `isContact` | bool | true если звонящий в контактах |

### vcp — структура

Формат: `"<длина>:8Ux<base64_protobuf>"`

Внутри — protobuf (field 30, wire type=2) с embedded JSON.
Бинарные protobuf-поля чередуются с текстовыми JSON-полями.

Декодирование: base64 → protobuf (первые 2 байта `0xf1 0x4c` — маркер) → JSON:

```python
_, b64 = vcp.split(':', 1)
if len(b64) % 4: b64 += '=' * (4 - len(b64) % 4)
decoded = base64.b64decode(b64)
text = decoded.decode('latin-1')
# Извлекаем JSON между { и }
```

Поля внутри JSON:

| Поле vcp | Тип | Описание |
|----------|-----|----------|
| `tkn` | string | WebSocket token для signaling сервера |
| `wse` | string | WebSocket URL видеосервера (`wss://videowebrtc.okcdn.ru/ws2`) |
| `ip` | array[string] | Список IP адресов медиа-серверов |
| `stn` | string | STUN URL |
| `tr` | string | TURN URL с username и credential |
| `srcp` | string | `"one_me"` (client source) |
| `iv` | bool | `true` = видео, `false` = аудио |
| `et` | int | Expire timestamp (unix seconds) |
| `u` | string | `"<tenant_id>:<signaling_uid>_"` — составной uid |
| `wt` | string | WebSocket transport endpoint |

### SUBSCRIBE_CHAT (opcode 75) — обязателен перед push 137

Для получения push 137 необходимо **подписаться на чат** через opcode 75.
Без подписки push 137 не приходит, даже с browser deviceId.

**Запрос:**
```json
{
  "opcode": 75,
  "payload": {
    "chatId": 309052361,
    "subscribe": true
  }
}
```

**Ответ:** `null` (при успехе)

**Таймлайн из HAR (входящий звонок):**
```
seq 21: SUBSCRIBE_CHAT(75) chatId=309052361      → response null
seq 22: NOTIF_TYPING(129) userId=307889134        → typing indicator
seq 23: NOTIF_INCOMING_CALL(137) callerId=307889134 → входящий звонок
```

Между SUBSCRIBE_CHAT и push 137 проходит ~40ms. После принятия звонка
клиент повторно подписывается на тот же чат (видимо, для гарантии
получения уведомлений на время звонка).

**Вывод:** для автоматизации приёма звонков нужно:
1. Открыть WS с browser deviceId
2. Подождать INIT и LOGIN
3. Вызвать SUBSCRIBE_CHAT для чата звонящего (chatId известен заранее)
4. Слушать opcode 137

### NOTIF_TYPING (opcode 129) — индикатор набора

Push-уведомление о том, что пользователь печатает. Приходит перед
входящим звонком — звонящий нажимает кнопку звонка, сервер посылает
typing, затем звонок.

```json
{
  "opcode": 129,
  "payload": {
    "chatId": 309052361,
    "userId": 307889134
  }
}
```

### NOTIF_PRESENCE (opcode 132) — уведомление о присутствии

Push-only! Отправка этого опкода как запроса **закрывает соединение**
с ошибкой `proto.opcode`. Только сервер может его отправлять.

```json
{
  "opcode": 132,
  "payload": {
    "presence": {
      "seen": 1781892741,
      "status": 1
    },
    "userId": 307889134
  }
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `presence.seen` | int | Timestamp последней активности (unix seconds) |
| `presence.status` | int | `1` = онлайн (отсутствует = офлайн) |
| `userId` | int | MAX user ID |

---

### Почему push 137 не приходит Python listeners?

Гипотеза: сервер отправляет opcode 137 только на **primary браузерное**
WebSocket соединение. Secondary Python WS с тем же токеном могут получать
другие пуши (128, 132 и т.д.), но opcode 137 фильтруется на сервере
по Connection-ID или Device-ID.

**Подтверждение:** в HAR-дампе все 4 push 137 пришли через единственное
WS #1 (ws-api.oneme.ru) — то же соединение, что и браузер.

### Решение: browser deviceId

Использование того же `deviceId`, что и в браузере, решает проблему.
Если в INIT передать `deviceId` из сессии web.max.ru, push 137 приходит
на Python WebSocket:

```python
# INIT с browser deviceId — push 137 приходит
device_id = "0a531fd8-6517-401a-990a-45fb6901a544"  # из web.max.ru
send(6, {"deviceId": device_id, "userAgent": {
    "deviceType": "WEB", "pushDeviceType": "WEBPUSH",
    "deviceName": "Browser",
    "headerUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "appVersion": "26.6.17", "screen": "1920x1080 2.0x",
    "timezone": "Europe/Moscow",
}})
```

Без browser deviceId (с уникальным `all_seeing` или UUID) — push 137
НЕ приходит, хотя другие пуши (128, 130, 132) работают.

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
| `count` | int | Количество записей (опционально, по умолчанию 50) |
| `marker` | int | Маркер для пагинации (backwardMarker или forwardMarker) |
| `direction` | string | Направление: `"backward"` (старше) или `"forward"` (новее) |

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
| `backwardMarker` | int | Маркер для пагинации назад (timestamp в мс) |
| `forwardMarker` | int | Маркер для пагинации вперёд (timestamp в мс) |

### Пагинация

**Назад (более старые):**
```json
{
  "chatId": 7268926,
  "count": 3,
  "marker": 1763036952192
}
```
или с явным direction:
```json
{
  "chatId": 7268926,
  "count": 3,
  "marker": 1763036952192,
  "direction": "backward"
}
```

**Вперёд (более новые):**
```json
{
  "chatId": 7268926,
  "count": 3,
  "marker": 1763041728128,
  "direction": "forward"
}
```

**Без маркера:** возвращает самые свежие записи.
**marker=0:** возвращает самые свежие записи (как без маркера).
**Без count:** возвращает до 50 записей.

### Ответ (пагинация назад)

```json
{
  "hasMore": true,
  "history": [...],
  "backwardMarker": 1763042244608,
  "forwardMarker": 1763042244608
}
```

### Особенности

- **hasMore** = true означает, что есть ещё записи в этом направлении
- **Сортировка:** от новых к старым
- **backwardMarker/forwardMarker** — timestamps в миллисекундах
- Значение маркеров меняется при каждой пагинации
- `duration = 0` означает пропущенный/отклонённый звонок
- `contactIds` всегда содержит один ID — ID собеседника (того, кому звонили)

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

`startActiveCall` на сервере — привязывает звонок (conversationId из signaling)
к чату. Используется для создания CALL-записи в истории и уведомления
собеседника о начале звонка.

> **ЭТОТ ОПКОД НЕ СОЗДАЁТ НОВЫЕ ЗВОНКИ.**
> Звонки создаются через HTTP API `vchat.startConversation` (см. выше).
> Opcode 78 — второй шаг: привязать уже созданный звонок к чату.

### Запрос

```json
{
  "isVideo": false,
  "conversationId": "uuid",
  "internalParams": ""
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|-------------|----------|
| `isVideo` | bool | да | `true` — видеозвонок, `false` — аудиозвонок |
| `conversationId` | string | да | UUID конференции (из startConversation) |
| `internalParams` | string | да | Любая строка (пустая `""` проходит) |
| `chatId` | int | нет | ID чата — если указан, callee берутся из чата |

### Сигнатура сервера

Из сообщения об ошибке восстановлена полная сигнатура:

```
CallsServiceImpl.startActiveCall(
  conversationId,          // string — UUID конференции
  userId,                  // int — ID текущего пользователя (из токена)
  <calleeUserIds>,         // ?? — NULL если не указан chatId
  remoteAddr,              // string — IP клиента (сервер определяет сам)
  isVideo,                 // boolean
  internalParams,          // string
  <extra>                  // ?? — всегда null
)
```

### Результаты тестирования

- **Без `chatId`**: ошибка `"Callee ids is empty"` — сервис не знает, кому звонить
- **С `chatId` (но пользователь не участник чата)**: `"not.chat.participant"` / `"Only chat participants are allowed to join chat call"`
- **С `chatId` + реальный conversationId**: `"not.chat.participant"` — т.к. conversationId не привязан к чату
- **`internalParams`**: строка (пустая `""` проходит). Любая непустая не-JSON строка → `"Invalid parameter internalParams value"`
  JSON-строка (`"{}"`, `'{"key":"val"}'`) → `UNKNOWN: Unexpected error` (краш сервера)
  Число/объект/массив → `"Expected string"` (валидация proto)
- **`calleeIds` / `externalIds` / `userId` / `contactId`**: любое extra поле → `"Missing required parameter internalParams"` — меняет поведение парсера

**Вывод:** CALL_START требует, чтобы текущий пользователь был участником
чата. Наш access_token (от web.max.ru) не даёт прав участника чата 7268926,
поэтому звонок не привязывается. Официальный клиент использует этот опкод
после startConversation для записи звонка в историю.

---

## Аналитика звонков (opcode 5)

При получении push 137 браузерный клиент отправляет аналитическое
событие `INCOMING_CALL_INIT`:

```json
{
  "opcode": 5,
  "payload": {
    "events": [{
      "type": "CALL",
      "userId": 3260455,
      "time": 1781893453263,
      "sessionId": 1781893446415,
      "event": "INCOMING_CALL_INIT",
      "params": {
        "call_id": "78CEBB15-E71F-443E-8F20-645E97495EA6",
        "event_label_int": 1,
        "is_group": false
      }
    }]
  }
}
```

Opcode 5 (NAV_ANALYTICS) используется для логирования навигации
и событий. Не является частью протокола звонка — клиент отправляет
его для внутренней аналитики.

## Опкоды звонков (сводка)

| Опкод | Название | Направление | Описание |
|-------|----------|-------------|----------|
| 5 | NAV_ANALYTICS | WS запрос | Аналитика звонков (INCOMING_CALL_INIT) |
| 69 | CALL_EDIT | WS запрос | Управление звонком (mute/close) |
| 75 | SUBSCRIBE_CHAT | WS запрос | Подписка на чат (обязательно перед push 137) |
| 78 | CALL_START | WS запрос | Подключение к звонку (не старт!) |
| 79 | CALL_HISTORY | WS запрос | История звонков в чате (с пагинацией) |
| 129 | NOTIF_TYPING | WS push | Индикатор набора (перед входящим звонком) |
| 132 | NOTIF_PRESENCE | WS push | Уведомление о присутствии (push-only!) |
| 137 | NOTIF_INCOMING_CALL | WS push | Уведомление о входящем звонке |
| 158 | CALL_TOKEN | WS запрос | Получение токена для HTTP API звонков |

## vchat.getHistory (HTTP API)

Дополнительный метод HTTP API для получения истории звонков,
созданных через HTTP API (в отличие от CALL_HISTORY, который
возвращает звонки официального клиента).

**Запрос:**
```
POST https://calls.okcdn.ru/fb.do
  method=vchat.getHistory
  format=JSON
  application_key=CNHIJPLGDIHBABABA
  session_key=<key>
```

**Ответ:**
```json
{
  "items": [
    {
      "type": "single",
      "conversation_id": "fdc70743-...",
      "user_id": "910173589479",
      "user_ids": ["910173589479"],
      "has_join_link": false,
      "id": 66325119647,
      "started_at": 1781887028417,
      "finished_at": 1781887034500,
      "is_inbound": false,
      "is_missed": false,
      "reach_status": "REACHED"
    }
  ]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | string | `"single"` |
| `conversation_id` | string | UUID конференции |
| `user_id` | string | Внутренний ID инициатора |
| `user_ids` | array[string] | Все участники |
| `has_join_link` | bool | Есть ли ссылка для присоединения |
| `id` | int | Внутренний ID записи |
| `started_at` | long | Timestamp начала (мс) |
| `finished_at` | long | Timestamp завершения (мс) |
| `is_inbound` | bool | Входящий ли звонок |
| `is_missed` | bool | Был ли пропущен |
| `reach_status` | string | `"REACHED"`, `"MISSED"`, `"REJECTED"` |

**Примечание:** user_id — это внутренний ID сессии звонков
(910173589479), а не ID пользователя в MAX (3260455).

## GET_SESSIONS (opcode 96)

Получение списка активных сессий пользователя (всех устройств).

**Запрос:**
```json
{
  "opcode": 96,
  "payload": {}
}
```

**Ответ:**
```json
{
  "sessions": [
    {
      "client": "MAX WEB",
      "current": true,
      "location": "Russian Federation",
      "info": "Python, Linux"
    }
  ]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `client` | string | Тип клиента: `MAX WEB`, `MAX iOS`, `MAX macOS Tahoe` |
| `current` | bool/null | Текущая сессия (`true`), или `null` |
| `location` | string | Страна |
| `info` | string | User-Agent строка |

## CONTACTS_PRESENCE (opcode 35)

Проверка статуса присутствия контакта.

**Запрос:**
```json
{
  "opcode": 35,
  "payload": {"contactIds": [6236697]}
}
```

**Ответ:**
```json
{
  "presence": {
    "6236697": {
      "seen": 1781884916
    }
  },
  "time": 1781886858366
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `presence.<user_id>.seen` | long | Timestamp последней активности (секунды) |
| `time` | long | Серверное время (мс) |

**Примечание:** Возвращает только `seen` timestamp для каждого
контакта. Нет поля `online`/`offline` — статус определяется
автоматически сервером на основе активности WebSocket.

## User ID mapping (из HAR)

| Система | ID | Описание |
|---------|----|----------|
| MAX userId (свой) | 3260455 | Владелец сессии |
| MAX userId (звонящий) | 307889134 | Кто звонит |
| Signaling user ID | 910111054239 | Внутренний ID для signaling (свой) |
| Signaling tenant ID | 921564..922252 | Изменяется между звонками (префикс uid в vcp) |
| Signaling participant ID (звонящий) | 1125899996294935 | ID звонящего в signaling |

## Опcode 130 — UNKNOWN_130 (CHAT_READ подтверждение)

```json
{
  "ver": 11,
  "cmd": 0,
  "opcode": 130,
  "payload": {
    "setAsUnread": false,
    "chatId": 309052361,
    "userId": 307889134,
    "mark": 1781890447978
  }
}
```

Push-уведомление, подтверждающее что сообщения в чате прочитаны.
Приходит когда **другой** участник прочитал сообщения (не сам).
userId — кто прочитал, chatId — какой чат.

---

## Источники

Базовая структура HTTP API звонков и signaling протокола была взята из
репозитория **[icyfalc0n/maxcalls](https://github.com/icyfalc0n/maxcalls)**
(Go-клиент для MAX Calls). Спасибо автору за анализ
базового протокола — от этой основы мы отталкивались в экспериментах
и дополняли деталями из реального трафика.

Документация публикуется в репозитории
**[pr0bel1230/max-api-docs](https://github.com/pr0bel1230/max-api-docs)**.
