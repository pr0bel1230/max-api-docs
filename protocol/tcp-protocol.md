# TCP протокол MAX (ver=10)

**Endpoint:** `api.oneme.ru:443` (SSL/TLS)  
**Формат:** MessagePack (бинарный фрейминг)  
**Версия:** 10

## Структура фрейма

Каждое сообщение — это 10-байтовый заголовок + msgpack payload:

### Заголовок (10 байт, big-endian)

```
struct.pack(">BBHHI", ver, cmd, seq, opcode, packed_len)

ver         = 10          # 1 байт — версия протокола
cmd         = 0           # 1 байт — 0=request, 1=response, 3=error
seq         = 1-255       # 2 байта — sequence number (seq % 256)
opcode      = 0-65535     # 2 байта — код операции
packed_len  = payload_len # 4 байта — длина payload (см. сжатие)
```

### Payload

После заголовка идёт тело длиной `packed_len & 0x00FFFFFF` байт.

Флаги (бит 24 `packed_len`):
- `flags & 0x1` — наличие ведущих ints (для ответов сервера)

### Сжатие

Бит 24 флага = 0x01000000 → payload сжат LZ4. Обычно ответы сервера
не сжаты (кроме больших LOGIN-ответов со списком чатов).

## Ведущие ints (Leading ints)

Ответы сервера всегда содержат 2 ведущих int перед msgpack-объектом.
Это не часть msgpack-структуры — их нужно прочитать и отбросить
перед msgpack.unpackb().

```python
offset = 0
ints = []
while offset < min(8, len(payload)):
    b = payload[offset]
    if b <= 0x7f:          # positive fixint
        ints.append(b); offset += 1
    elif 0xe0 <= b <= 0xff: # negative fixint
        ints.append(b - 256); offset += 1
    elif b == 0xd0:         # int8
        ints.append(struct.unpack('b', payload[offset+1])[0]); offset += 2
    elif b == 0xd1:         # int16
        ints.append(struct.unpack('>h', payload[offset+1:offset+3])[0]); offset += 3
    elif b == 0xd2:         # int32
        ints.append(struct.unpack('>i', payload[offset+1:offset+5])[0]); offset += 5
    else: break

# После ведущих ints — обычная msgpack структура
obj = msgpack.unpackb(payload[offset:], raw=False)
```

Примеры ведущих ints:
- INIT response: `f0 4b` = (-16, 75)
- LOGIN response: `f4 2f` = (-12, 47)
- MSG_DELETE response: `f0 13` = (-16, 19)
- MSG_SEND response: `f0 11` = (-16, 17)

## Полный цикл запроса

### 1. SSL/TLS handshake

```python
import ssl, socket, certifi

ctx = ssl.create_default_context(cafile=certifi.where())
sock = ctx.wrap_socket(socket.socket(), server_hostname="api.oneme.ru")
sock.connect(("api.oneme.ru", 443))
```

### 2. INIT (opcode 6)

```python
seq += 1
send_frame(sock, 10, 0, seq, 6, {
    "userAgent": {
        "deviceType": "WEB",
        "locale": "ru",
        "deviceLocale": "ru",
        "osVersion": "Linux",
        "deviceName": "Firefox",
        "headerUserAgent": "Mozilla/5.0",
        "appVersion": "25.11.1",
        "screen": "1080x1920 1.0x",
        "timezone": "Asia/Yekaterinburg"
    },
    "deviceId": "<device_id>"
})
# response: cmd=1 opcode=6
```

### 3. LOGIN (opcode 19)

```python
seq += 1
send_frame(sock, 10, 0, seq, 19, {
    "interactive": True,
    "token": "<access_token>",
    "chatsCount": 100,
    "chatsSync": 100,
    "contactsSync": 0,
    "presenceSync": 0,
    "draftsSync": 0
})
# response: cmd=1 opcode=19, payload = профиль + чаты
```

### 4. DELETE (opcode 66)

```python
seq += 1
send_frame(sock, 10, 0, seq, 66, {
    "chatId": 7268926,
    "messageIds": [116762203424780659],
    "forMe": False
})
```

## Особенности msgpack

Библиотека `msgpack` (pip install msgpack) не умеет парсить некоторые
MAX-специфичные байты:

- **0xc6** — нестандартный байт, используемый MAX как маркер. Приводит к
  ошибке "extra data" в msgpack.unpackb. Решение — удалить или обойти.
- **ext коды > 127** — невалидны по спецификации msgpack, но MAX их
  использует. Обрабатывать как raw bytes.

## Утилиты

```python
import struct, msgpack

def pack_frame(ver, cmd, seq, opcode, payload=None):
    pb = msgpack.packb(payload or {}, use_bin_type=True)
    return struct.pack(">BBHHI", ver, cmd, seq, opcode, len(pb)) + pb

def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("closed")
        data += chunk
    return data

def recv_frame(sock):
    header = recv_exact(sock, 10)
    ver, cmd, seq, opcode, packed = struct.unpack(">BBHHI", header)
    plen = packed & 0x00FFFFFF
    payload = recv_exact(sock, plen) if plen else b""
    return {'ver': ver, 'cmd': cmd, 'seq': seq, 'opcode': opcode, 'payload': payload}
```
