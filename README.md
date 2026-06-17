# MAX Messenger API Documentation

Документация протокола мессенджера MAX (oneme.ru), полученная методом
reverse engineering.

## Предназначение

Этот репозиторий содержит техническое описание закрытого протокола
MAX Messenger — мессенджера, встроенного в экосистему MAX.
Официальной публичной документации API не существует; всё, что здесь
написано, получено анализом трафика и исходного кода веб-клиента.

## Структура

```
max-api-docs/
├── README.md                              # Этот файл
├── protocol/
│   ├── opcodes.md                         # Полная таблица опкодов
│   ├── auth.md                            # Аутентификация (INIT, LOGIN)
│   ├── messaging.md                       # Сообщения (send, delete, history)
│   ├── chats.md                           # Чаты (список, управление)
│   ├── contacts.md                        # Контакты и профиль
│   ├── files.md                           # Загрузка и отправка файлов
│   ├── push.md                            # Push-уведомления
│   ├── tcp-protocol.md                    # TCP протокол (MessagePack, ver=10)
│   └── websocket.md                       # WebSocket протокол (JSON, ver=11)
└── scripts/
    ├── mcp-max-user-server.py             # MCP сервер для AI-ассистентов
    └── tests/
        ├── tcp_delete.py                  # DELETE-запрос через TCP (opcode 66)
        ├── delete_variants.py             # Сканирование опкодов
        └── tcp_raw_test.py                # Дампы INIT/LOGIN
```

## Транспорт

MAX использует два параллельных протокола:

| Транспорт | Endpoint | Формат | Версия |
|-----------|----------|--------|--------|
| WebSocket | `wss://ws-api.oneme.ru/websocket` | JSON | 11 |
| TCP (SSL) | `api.oneme.ru:443` | MessagePack | 10 |

Оба используют одинаковую систему опкодов и payload.
Подключение: **INIT (6)** → **LOGIN (19)** → рабочие запросы.

## Быстрый старт

```bash
pip install websocket-client msgpack certifi

export ACCESS_TOKEN="токен из web.max.ru"
export DEVICE_ID="device_id из INIT запроса"

python3 scripts/tests/tcp_delete.py
```

**Как получить токены:**
1. Открой [web.max.ru](https://web.max.ru) в Chrome/Firefox
2. F12 → Network → фильтр WS
3. Найди INIT (opcode=6) — там `deviceId`
4. Найди LOGIN (opcode=19) — там `token`

## Основные опкоды

| Опкод | Команда | Назначение |
|-------|---------|------------|
| 6 | INIT | Инициализация сессии |
| 19 | LOGIN | Авторизация |
| 49 | GET_HISTORY | История сообщений |
| 64 | MSG_SEND | Отправка сообщения |
| 65 | MSG_TYPING | Индикатор печатания |
| 66 | MSG_DELETE | Удаление сообщения |
| 67 | MSG_EDIT | Редактирование |
| 87 | FILE_UPLOAD | Загрузка файла |
| 92 | MSG_DELETE_RANGE | Массовое удаление |

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

## История исследования

Как это начиналось. В одной из реализаций MAX API, гуляющих по сети,
удаление сообщений было завязано на опкод 65. Запрос уходит, сервер
отвечает `cmd=1` — всё выглядит как успех. Сообщение не удаляется.

Несколько часов ушло на то, чтобы понять: сервер отвечает `cmd=1`
на любой корректный запрос. Это не подтверждение операции — это
подтверждение, что запрос дошёл. А опкод 65 оказался MSG_TYPING —
индикатором набора текста. Иными словами, всё это время мы не удаляли
сообщения, а просто сообщали собеседнику, что «печатаем».

Решение пришло из систематического перебора. Скрипт `delete_variants.py`
гонял один и тот же DELETE-запрос через опкоды 65–92 и смотрел, какой
из них даёт не просто `cmd=1`, а осмысленный ответ с данными.
Им оказался опкод 66 — настоящий MSG_DELETE. Первое же удаление
подтвердилось запросом истории: сообщение исчезло.

После этого карта опкодов собралась быстро — каждый подтверждался
экспериментально, отправкой реального запроса и проверкой результата.
Часть структур payload (вроде полей в MSG_SEND) подсмотрена в
JavaScript-бандлах веб-клиента.

Репозиторий появился, потому что такой информации в открытом доступе
нет. Если вы пишете под MAX — эта документация сэкономит вам
несколько часов. Мы свои уже потратили.

## Лицензия

MIT
