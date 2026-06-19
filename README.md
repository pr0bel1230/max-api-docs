# Документация API мессенджера MAX (Messenger MAX API Documentation)

Документация протокола российского мессенджера [MAX (МАКС)](https://max.ru/), полученная методом
reverse engineering.

## Предназначение

Этот репозиторий содержит техническое описание закрытого протокола API
MAX — мессенджера, созданного компанией VK.
Официальной публичной документации API не существует; всё, что здесь
написано, получено анализом трафика.

## Структура

```
max-api-docs/
├── README.md                              # Этот файл
├── protocol/
│   ├── opcodes.md                         # Полная таблица опкодов
│   ├── auth.md                            # Аутентификация (INIT, LOGIN)
│   ├── messaging.md                       # Сообщения (send, delete, history, search)
│   ├── chats.md                           # Чаты (список, управление, upload)
│   ├── contacts.md                        # Контакты и профиль
│   ├── files.md                           # Загрузка и отправка файлов
│   ├── calls.md                           # Звонки (история, старт, управление)
│   ├── presets.md                         # Пресеты (аватары, стикеры, эмодзи)
│   ├── push.md                            # Push-уведомления
│   ├── connection.md                      # Управление сессией (MaxConnection vs probe)
│   ├── tcp-protocol.md                    # TCP протокол (MessagePack, ver=10)
│   └── websocket.md                       # WebSocket протокол (JSON, ver=11)
└── scripts/
    └── example.py                         # Пример работы с MAX API
```

## Транспорт

MAX использует два параллельных протокола:

| Транспорт | Endpoint | Формат | Версия |
|-----------|----------|--------|--------|
| WebSocket | `wss://ws-api.oneme.ru/websocket` | JSON | 11 |
| TCP (SSL) | `api.oneme.ru:443` | MessagePack | 10 |

Оба используют одинаковую систему опкодов и payload.
Подключение: **INIT (6)** → **LOGIN (19)** → рабочие запросы.

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
1. Авторизуйся на [web.max.ru](https://web.max.ru) в Chrome/Firefox
2. F12 → Network → перезагрузи страницу (F5)
3. В фильтре выбери `WS` (WebSocket)
4. Кликни на соединение `wss://ws-api.oneme.ru/websocket`
5. Первое сообщение (INIT, opcode=6) → payload содержит `deviceId`
6. Второе сообщение (LOGIN, opcode=19) → payload содержит `token`

## Основные опкоды

| Опкод | Команда | Назначение |
|-------|---------|------------|
| 6 | INIT | Инициализация сессии |
| 19 | LOGIN | Авторизация |
| 25 | GET_PRESET_AVATARS | Пресеты аватаров |
| 26 | GET_PRESETS | Стикеры, эмодзи, реакции |
| 53 | GET_CHATS | Список чатов |
| 61 | GET_CHAT_INFO | Информация о чате |
| 64 | MSG_SEND | Отправка сообщения |
| 65 | MSG_TYPING | Индикатор печатания |
| 66 | MSG_DELETE | Удаление сообщения |
| 67 | MSG_EDIT | Редактирование |
| 69 | CALL_EDIT | Управление звонком |
| 70 | FORWARD_MESSAGE | Пересылка сообщения |
| 73 | SEARCH_MESSAGES | Поиск по сообщениям |
| 77 | CHAT_OPERATION | Операции с чатами |
| 78 | CALL_START | Инициализация звонка |
| 79 | CALL_HISTORY | История звонков |
| 80 | IMAGE_UPLOAD_URL | URL загрузки изображений |
| 81 | IMAGE_UPLOAD_IUSMILE | URL загрузки (iusmile) |
| 86 | CHAT_SHOW | Управление отображением чата |
| 87 | FILE_UPLOAD | Загрузка файла |
| 92 | CHAT_ACTIVITY | Информация о чате за период |
| 272 | GET_FOLDERS | Папки чатов |

Полная таблица → [protocol/opcodes.md](protocol/opcodes.md)

**Примечание:** Сервер отвечает `cmd=1` (ACK) на любой корректный
запрос, даже если операция не поддерживается. Проверять реальный
эффект нужно через запрос данных (GET_HISTORY).

## Источники

Документация составлена на основе:

- **Исходный код веб-клиента** — JavaScript-бандлы `web.max.ru`,
  содержат полную карту опкодов и структуры payload
- **WebSocket-трафик** — анализ запросов/ответов через DevTools
- **Прямое тестирование** — отправка запросов напрямую через TCP
  сокеты и WebSocket с различными опкодами и payload
- **Экспериментальная верификация** — проверка эффекта операций
  через запросы состояния (GET_HISTORY, GET_CHATS)

### Сторонние источники

- [MaxProtoExplanation](https://github.com/nyakokitsu/MaxProtoExplanation) —
  объяснение бинарного протокола oneme TCP: структура фрейма, msgpack,
  LZ4-сжатие
- [maxcalls](https://github.com/icyfalc0n/maxcalls) — документация
  WebSocket API, описание аутентификации и опкодов звонков
- [max-api](https://kirill7mix.github.io/maxapi/) — неофициальная Python
  библиотека с таблицей 100+ опкодов
- [PyMax](https://github.com/MaxApiTeam/PyMax) — Python-клиент MAX,
  коммуникационные протоколы (DeepWiki)
- [openmax-server](https://github.com/openmax-team/server) — открытая
  реализация сервера MAX, oneme TCP wire protocol (DeepWiki)
- [vk-max](https://github.com/larytet-assorted/vk-max) —
  декомпилированный Android-клиент MAX (VK)
- [Клиент MAX на Rust](https://dtf.ru/software/3887805-klient-dlya-messendzhera-max-na-rust) —
  статья на DTF о reverse engineering MAX
- [python-max-client](https://pypi.org/project/python-max-client/) —
  ещё одна Python-реализация клиента
- [OSINT Anatomy: слежка за VPN](https://osintech.substack.com/p/osint-anatomy-does-max-messenger) —
  исследование телеметрии MAX
- [madmax](https://pypi.org/project/madmax/) — Python-пакет
  для работы с MAX API

## Лицензия

MIT
