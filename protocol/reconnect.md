# Graceful Reconnect

MAX WebSocket-соединения непостоянны: сервер закрывает неактивные
соединения, токены сбрасываются, возможны сетевые проблемы.
Клиент должен быть готов переподключаться.

## Когда нужно переподключаться

1. **Таймаут неактивности** — сервер закрывает соединение через
   ~30-60 секунд простоя. PING (opcode 1) с `{"interactive": true}`
   продлевает сессию.
2. **Сброс токена** — после ~30-50 LOGIN-ов с одним токеном за
   короткий промежуток сервер перестаёт принимать INIT.
   Требуется свежий токен из web.max.ru.
3. **Сетевой обрыв** — потеря соединения из-за сети.
4. **Ошибка протокола** — невалидный запрос может привести
   к закрытию соединения сервером.

## Базовая стратегия переподключения

```python
import json, time, ssl
from websocket import create_connection
import certifi

def connect():
    """Создать новое соединение: INIT → LOGIN."""
    ws = create_connection(
        "wss://ws-api.oneme.ru/websocket",
        sslopt={"ca_certs": certifi.where()},
        timeout=15
    )
    # INIT
    ws.send(json.dumps({
        "ver": 11, "cmd": 0,
        "seq": int(time.time() * 1000) & 0xFFFF,
        "opcode": 6,
        "payload": {
            "deviceId": DEVICE_ID,
            "userAgent": {
                "deviceType": "WEB", "locale": "ru",
                "deviceLocale": "ru", "osVersion": "Linux",
                "deviceName": "Firefox",
                "headerUserAgent": "Mozilla/5.0",
                "appVersion": "25.11.1",
                "screen": "1080x1920 1.0x",
                "timezone": "Asia/Yekaterinburg"
            }
        }
    }))
    json.loads(ws.recv())  # INIT OK
    # LOGIN
    ws.send(json.dumps({
        "ver": 11, "cmd": 0,
        "seq": int(time.time() * 1000) & 0xFFFF,
        "opcode": 19,
        "payload": {
            "token": TOKEN,
            "interactive": True,
            "chatsCount": 5, "chatsSync": 5,
            "contactsSync": 0, "presenceSync": 0, "draftsSync": 0
        }
    }))
    json.loads(ws.recv())  # LOGIN OK
    return ws

def reconnect(max_retries=5, delay=2):
    """Переподключиться с экспоненциальной задержкой."""
    for attempt in range(max_retries):
        try:
            return connect()
        except Exception as e:
            wait = delay * (2 ** attempt)
            print(f"Reconnect failed ({attempt+1}/{max_retries}): {e}")
            time.sleep(wait)
    raise Exception("Max reconnection attempts exceeded")
```

## Экспоненциальная задержка (Exponential Backoff)

При повторных ошибках увеличивайте паузу между попытками:

```
attempt 1: ждать 2 сек
attempt 2: ждать 4 сек
attempt 3: ждать 8 сек
attempt 4: ждать 16 сек
attempt 5: ждать 32 сек
```

Это предотвращает «шквал» повторных подключений, который может
усугубить проблему (например, ускорить сброс токена).

## Heartbeat (PING)

Для поддержания соединения клиент должен периодически отправлять
PING и отвечать на PING от сервера.

**Ping от сервера (push):**
```json
{
  "ver": 11, "cmd": 0,
  "opcode": 1,
  "payload": {}
}
```

**Ответ клиента:**
```json
{
  "ver": 11, "cmd": 0,
  "opcode": 1,
  "seq": 12345,
  "payload": {"interactive": true}
}
```

**Рекомендуемый интервал:** отправлять PING раз в 15 секунд,
если нет другого трафика.

```python
import threading

def heartbeat(ws, interval=15):
    """Фоновый поток для поддержания соединения."""
    def ping():
        while True:
            time.sleep(interval)
            try:
                ws.send(json.dumps({
                    "ver": 11, "cmd": 0,
                    "seq": int(time.time() * 1000) & 0xFFFF,
                    "opcode": 1,
                    "payload": {"interactive": True}
                }))
            except:
                break
    t = threading.Thread(target=ping, daemon=True)
    t.start()
```

## Рекомендации

1. **Одно соединение на сессию** — не создавайте новое соединение
   на каждый запрос. Это сжигает лимит LOGIN-ов токена.
2. **seq-матчинг** — используйте seq для сопоставления ответов
   с запросами (см. [connection.md](connection.md)).
3. **Таймауты** — ставьте разумные таймауты (15-30 секунд) на
   соединение. Слишком короткий таймаут вызовет ложные срабатывания.
4. **Фильтр push** — при переподключении могут прийти push-уведомления,
   накопленные за время простоя. Отфильтровывайте их по `cmd=0`.
5. **DEVICE_ID** — используйте уникальный deviceId для каждого
   соединения, если несколько клиентов работают с одним токеном.
   Иначе сервер может закрыть одно из соединений.
