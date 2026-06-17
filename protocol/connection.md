# Соединение и управление сессией

MAX API использует WebSocket-соединение. В отличие от HTTP, WebSocket
позволяет отправлять множество запросов в рамках одного соединения.

## probe() — устаревший подход (НЕ ИСПОЛЬЗОВАТЬ)

В ранних скриптах использовался паттерн `probe()` — одно соединение
на один запрос:

```python
def probe(op, pl):
    ws = create_connection(...)
    ws.send(INIT)
    ws.send(LOGIN)
    # ... wait for login ...
    ws.send({"opcode": op, "payload": pl})
    # ... wait for response ...
    ws.close()
    return result
```

**Проблемы:**
1. **Сжигает токен.** Каждый вызов probe() = полный INIT + LOGIN.
   10-20 запросов = 10-20 LOGIN-событий. Сервер сбрасывает токен
   по превышению лимита LOGIN-ов (обычно после ~30-50).
2. **Медленный.** Каждый запрос требует установки WebSocket-соединения
   (~200-500 мс на TLS handshake) и полного цикла INIT+LOGIN.
3. **Артефакты.** При закрытии соединения сервер может выполнять
   дополнительные действия (очистка сессии), что маскирует поведение
   опкодов.

## MaxConnection — persistent-соединение (РЕКОМЕНДУЕТСЯ)

Одно WebSocket-соединение на всю сессию. Один INIT, один LOGIN,
множество запросов:

```python
from max_connection import MaxConnection

conn = MaxConnection(token, device_id)
r1 = conn.request(64, {"chatId": ..., "message": {...}})
r2 = conn.request(71, {"chatId": ..., "messageIds": [...]})
r3 = conn.request(49, {"chatId": ..., "backward": 10, ...})
conn.close()
```

**Преимущества:**
- **1 LOGIN на сессию** — токен не сгорает
- **seq-матчинг** — каждый запрос имеет уникальный seq, ответ матчится
  по seq, а не по порядку
- **Push-уведомления игнорируются** — cmd=0 (push) отфильтровывается
- **Auto-reconnect** — при обрыве соединения пытается переподключиться
- **В 5-10 раз быстрее** — нет оверхеда на установку соединения

### Пример

```python
import json
from max_connection import MaxConnection

cfg = json.load(open("config.json"))
conn = MaxConnection(cfg["access_token"], cfg["device_id"])

# Отправить сообщение
r = conn.request(64, {"chatId": 7268926, "message": {
    "text": "Привет!", "cid": 1734567890123, "elements": [], "attaches": []}})
msg_id = r["payload"]["message"]["id"]

# Проверить, что оно существует
r = conn.request(71, {"chatId": 7268926, "messageIds": [msg_id]})
assert len(r["payload"]["messages"]) > 0

# Удалить с forMe=True (безопасно)
r = conn.request(66, {"chatId": 7268926, "messageIds": [msg_id], "forMe": True})

conn.close()
```

### Обработка ошибок

```python
from max_connection import MaxConnection, MaxAuthError, MaxTimeoutError

try:
    conn = MaxConnection(token, device_id)
    r = conn.request(op, payload)
except MaxAuthError:
    print("Токен истёк — обновите access_token")
except MaxTimeoutError:
    print("Таймаут — сервер не ответил")
```

### Максимальное количество запросов

Проверено: **25+ запросов** на одном соединении без потери стабильности.
Ограничение, вероятно, задаётся сервером (таймаут неактивности).
При обрыве соединения MaxConnection автоматически переподключается.

## Сравнение производительности

| Параметр | probe() | MaxConnection |
|----------|---------|---------------|
| LOGIN-событий на 20 запросов | 20 | 1 |
| Время выполнения 20 запросов | ~15-20 с | ~2-4 с |
| Риск сгорания токена | Высокий | Низкий |
| Поддержка seq | Нет | Да |
| Фильтрация push | Нет | Да |
| Auto-reconnect | Нет | Да |
