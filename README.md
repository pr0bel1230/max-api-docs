# Документация API мессенджера MAX (Messenger MAX API Documentation)

Документация протокола российского мессенджера [MAX (МАКС)](https://max.ru/), полученная методом
reverse engineering.

## Что такое MAX API?

MAX — мессенджер компании VK. Его API работает через WebSocket или TCP:
клиент подключается к серверу и обменивается JSON-сообщениями.

**Опкод (opcode)** — это номер действия. Каждый запрос — число-команда
с данными (payload). Например:
- `opcode 64` с payload `{"text": "Привет"}` → отправить сообщение
- `opcode 53` → получить список чатов
- `opcode 19` → авторизоваться

Сервер отвечает аналогичной структурой: опкод + данные.

## Формат запроса и ответа

```json
{
  "ver": 11,        // версия протокола
  "cmd": 0,         // 0 = запрос, 1 = ответ (ACK), 3 = ошибка
  "seq": 12345,     // номер запроса (для сопоставления ответа)
  "opcode": 64,     // номер команды
  "payload": {}     // данные запроса/ответа
}
```

Все поля обязательны. `cmd=1` — успех, `cmd=3` — ошибка (проверяй `payload.error`).

## Подключение

Любая сессия начинается с двух обязательных шагов:

**INIT (6)** → инициализация, передаёшь `deviceId`
**LOGIN (19)** → авторизация, передаёшь `token`

После этого можно отправлять любые рабочие запросы.

## Транспорт

MAX использует два параллельных протокола с одинаковой системой опкодов:

| Транспорт | Endpoint | Формат | Версия |
|-----------|----------|--------|--------|
| WebSocket | `wss://ws-api.oneme.ru/websocket` | JSON | 11 |
| TCP (SSL) | `api.oneme.ru:443` | MessagePack | 10 |

WebSocket проще для начала — все данные в читаемом JSON.
TCP использует бинарный фрейм (MessagePack + LZ4).

## С чего начать читать

Если видишь репозиторий впервые — вот порядок:

1. **[protocol/tcp-protocol.md](protocol/tcp-protocol.md)** или **[protocol/websocket.md](protocol/websocket.md)** — выбери транспорт
2. **[protocol/auth.md](protocol/auth.md)** — INIT, LOGIN (обязательно)
3. **[protocol/connection.md](protocol/connection.md)** — управление сессией (seq-матчинг, таймауты)
4. **[protocol/messaging.md](protocol/messaging.md)** — отправка и получение сообщений
5. **[protocol/chats.md](protocol/chats.md)** — управление чатами
6. **[protocol/opcodes.md](protocol/opcodes.md)** — все опкоды (справочник)

Остальные файлы — по необходимости (файлы, звонки, пресеты, push).

## Структура репозитория

```
max-api-docs/
├── protocol/
│   ├── opcodes.md              # Полная таблица опкодов (справочник)
│   ├── auth.md                 # Аутентификация (INIT, LOGIN, SMS)
│   ├── messaging.md            # Сообщения (send, delete, history, search)
│   ├── chats.md                # Чаты (список, управление, upload)
│   ├── contacts.md             # Контакты и профиль
│   ├── files.md                # Загрузка и отправка файлов
│   ├── calls.md                # Звонки (история, старт, управление)
│   ├── calls-security.md       # Безопасность звонков (DTLS, SRTP, CSP)
│   ├── presets.md              # Пресеты (аватары, стикеры, эмодзи)
│   ├── push.md                 # Push-уведомления
│   ├── connection.md           # Управление сессией
│   ├── elements.md             # Rich-элементы (форматирование текста)
│   ├── error-codes.md          # Справочник ошибок
│   ├── reconnect.md            # Graceful Reconnect и heartbeat
│   ├── tcp-protocol.md         # TCP протокол (MessagePack, ver=10)
│   └── websocket.md            # WebSocket протокол (JSON, ver=11)
└── scripts/
    └── example.py              # Пример работы с MAX API
```

## Пример работы

```bash
pip install websocket-client certifi

export ACCESS_TOKEN="токен из web.max.ru"
export DEVICE_ID="device_id из INIT запроса"

python3 scripts/example.py
```

Скрипт [scripts/example.py](scripts/example.py) показывает:
- INIT (opcode 6) — инициализация сессии
- LOGIN (opcode 19) — авторизация
- GET_CHATS (opcode 53) — список чатов
- GET_HISTORY (opcode 49) — история сообщений
- MSG_SEND (opcode 64) — отправка сообщения

**Как получить токены:**
1. Открой [web.max.ru](https://web.max.ru) в Chrome/Firefox
2. F12 → Network → перезагрузи страницу (F5)
3. В фильтре выбери `WS` (WebSocket)
4. Кликни на соединение `wss://ws-api.oneme.ru/websocket`
5. Первое сообщение (INIT, opcode=6) → payload содержит `deviceId`
6. Второе сообщение (LOGIN, opcode=19) → payload содержит `token`

## Основные опкоды

| Опкод | Команда | Назначение |
|-------|---------|------------|
| 6 | INIT | Инициализация сессии |
| 17 | VERIFICATION_REQUEST | SMS-запрос кода авторизации |
| 18 | CODE_ENTER | Подтверждение кода из SMS |
| 19 | LOGIN | Авторизация |
| 25 | GET_PRESET_AVATARS | Пресеты аватаров |
| 26 | GET_PRESETS | Стикеры, эмодзи, реакции |
| 49 | GET_HISTORY | История сообщений |
| 53 | GET_CHATS | Список чатов |
| 55 | VOID | Heartbeat чатов / заглушка |
| 61 | GET_CHAT_INFO | Информация о чате |
| 64 | MSG_SEND | Отправка сообщения |
| 65 | MSG_TYPING | Индикатор печатания |
| 66 | MSG_DELETE | Удаление сообщения |
| 67 | MSG_EDIT | Редактирование |
| 69 | CALL_EDIT | Управление звонком |
| 70 | FORWARD_MESSAGE | Пересылка сообщения |
| 73 | SEARCH_MESSAGES | Поиск по сообщениям |
| 77 | CHAT_OPERATION | Операции с чатами |
| 78 | CALL_START | Подключение к звонку |
| 79 | CALL_HISTORY | История звонков |
| 137 | NOTIF_INCOMING_CALL | Push: входящий звонок |
| 158 | CALL_TOKEN | Токен для HTTP API звонков |
| 80 | IMAGE_UPLOAD_URL | URL загрузки изображений |
| 81 | IMAGE_UPLOAD_IUSMILE | URL загрузки (iusmile) |
| 86 | CHAT_SHOW | Управление отображением чата |
| 87 | FILE_UPLOAD | Загрузка файла |
| 92 | CHAT_ACTIVITY | Информация о чате за период |
| 272 | GET_FOLDERS | Папки чатов |
| 200 | SERVER_TIME | Серверное время |
| 302 | GET_BANNERS | Баннеры приложения |

Полная таблица → [protocol/opcodes.md](protocol/opcodes.md)

**Примечание:** Сервер отвечает `cmd=1` (ACK) на любой корректный
запрос, даже если операция не поддерживается. Проверять реальный
эффект нужно через запрос данных (GET_HISTORY).

## Источники

Документация составлена на основе:
- **WebSocket-трафик** — анализ запросов/ответов через DevTools
- **Прямое тестирование** — отправка запросов через TCP и WebSocket с разными опкодами и payload
- **Сторонние проекты** (полученные тем же методом):
  - [**maxcalls**](https://github.com/icyfalc0n/maxcalls) (Go) — базовая структура HTTP API звонков и signaling протокола.
    Спасибо автору.
  - [PyMax](https://github.com/MaxApiTeam/PyMax)
  - [openmax-server](https://github.com/openmax-team/server)
  - [python-max-client](https://pypi.org/project/python-max-client/)
  - [madmax](https://pypi.org/project/madmax/)

## Лицензия

MIT
