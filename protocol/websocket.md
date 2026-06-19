# WebSocket протокол MAX (ver=11)

**Endpoint:** `wss://ws-api.oneme.ru/websocket`  
**Формат:** JSON (текстовые фреймы)  
**Версия:** 11

## Структура сообщения

Все сообщения — JSON-объекты с фиксированной структурой:

```json
{
  "ver": 11,
  "cmd": 0,
  "seq": 3,
  "opcode": 66,
  "payload": { ... }
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `ver` | int | Версия протокола (11) |
| `cmd` | int | 0=запрос, 1=ответ, 3=ошибка |
| `seq` | int | Порядковый номер (начинается с 1) |
| `opcode` | int | Код операции |
| `payload` | object | Тело запроса/ответа |

## Sub-protocol

При подключении WebSocket используется без sub-protocol, только заголовки:

```
Origin: https://web.max.ru
User-Agent: Mozilla/5.0
```

## Полный цикл

### 1. Подключение и INIT

```python
from websocket import create_connection

ws = create_connection("wss://ws-api.oneme.ru/websocket",
    header=[
        "Origin: https://web.max.ru",
        "User-Agent: Mozilla/5.0"
    ],
    timeout=10)

ws.send(json.dumps({
    "ver": 11, "cmd": 0, "seq": 1, "opcode": 6,
    "payload": {
        "userAgent": {
            "deviceType": "WEB", "locale": "ru",
            "deviceLocale": "ru", "osVersion": "Linux",
            "deviceName": "Firefox",
            "headerUserAgent": "Mozilla/5.0",
            "appVersion": "25.11.1",
            "screen": "1080x1920 1.0x",
            "timezone": "Asia/Yekaterinburg"
        },
        "deviceId": "<device_id>"
    }
}))
```

### 2. LOGIN

```python
ws.send(json.dumps({
    "ver": 11, "cmd": 0, "seq": 2, "opcode": 19,
    "payload": {
        "interactive": True,
        "token": "<access_token>",
        "chatsCount": 100,
        "chatsSync": 100,
        "contactsSync": 0,
        "presenceSync": 0,
        "draftsSync": 0
    }
}))

# Ожидание ответа LOGIN
for _ in range(5):
    resp = json.loads(ws.recv())
    if resp.get("cmd") == 1 and resp.get("opcode") == 19:
        print("LOGIN успешен")
        break
```

### 3. Отправка сообщения

```python
ws.send(json.dumps({
    "ver": 11, "cmd": 0, "seq": 3, "opcode": 64,
    "payload": {
        "chatId": 7268926,
        "message": {
            "text": "Привет!",
            "cid": int(time.time() * 1000),
            "elements": [],
            "attaches": []
        },
        "notify": True
    }
}))
```

Ответ содержит `message.id` — числовой ID сообщения в виде строки:

```json
{
  "cmd": 1, "seq": 3, "opcode": 64,
  "payload": {
    "message": {
      "id": "116762203424780659",
      ...
    }
  }
}
```

### 4. Удаление сообщения

```python
ws.send(json.dumps({
    "ver": 11, "cmd": 0, "seq": 4, "opcode": 66,
    "payload": {
        "chatId": 7268926,
        "messageIds": [116762203424780659],
        "forMe": False
    }
}))
```

## Чтение ответов

В отличие от TCP, WebSocket ответы читаются как JSON-объекты.
Номер `seq` в ответе совпадает с номером запроса — это основной
способ сопоставить ответ и запрос.

```python
_seq = 0
def request(ws, opcode, payload, timeout=15):
    """Отправить запрос, дождаться ответа с тем же seq."""
    global _seq
    _seq += 1
    seq = _seq
    ws.send(json.dumps({
        "ver": 11, "cmd": 0,
        "seq": seq, "opcode": opcode,
        "payload": payload
    }))
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = json.loads(ws.recv())
        if resp.get("cmd") == 1 and resp.get("seq") == seq:
            return resp["payload"]
```

> **⚠️ Для продакшн-использования изучите [connection.md](connection.md) —**
> persistent-соединение, seq-матчинг и таймауты.
> Код выше — только для понимания wire-протокола.

## Отличия от TCP

| Аспект | WebSocket (ver=11) | TCP (ver=10) |
|--------|-------------------|--------------|
| Формат | JSON | MessagePack |
| Ведущие ints | Нет | Есть (2 байта) |
| seq | Любое число | seq % 256 |
| Сжатие | Нет | LZ4 опционально |
| Декодирование | json.loads | msgpack.unpackb |
