#!/usr/bin/env python3
"""
TCP MSG_DELETE (opcode 66) — минимальный работающий пример.

Использование:
    export ACCESS_TOKEN="токен из web.max.ru"
    export DEVICE_ID="device_id из INIT запроса"
    python3 tcp_delete.py
"""
import json
import os
import ssl
import struct
import sys
import socket
import time
import mgpack
import certifi

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN") or sys.exit("❌ Укажи ACCESS_TOKEN")
DEVICE_ID = os.environ.get("DEVICE_ID") or sys.exit("❌ Укажи DEVICE_ID")
CHAT_ID = int(os.environ.get("CHAT_ID", "7268926"))
MESSAGE_TEXT = f"DELETE test {time.strftime('%H:%M:%S')}"

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())


# ─── TCP helpers ───

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
    h = recv_exact(sock, 10)
    _, cmd, _, op, pl = struct.unpack(">BBHHI", h)
    plen = pl & 0x00FFFFFF
    return {
        'cmd': cmd,
        'opcode': op,
        'plen': plen,
        'payload': recv_exact(sock, plen) if plen else b""
    }

def tcp_connect():
    """TCP connection → INIT → LOGIN. Returns (sock, seq)."""
    sock = _ssl_ctx.wrap_socket(socket.socket(), server_hostname="api.oneme.ru")
    sock.settimeout(15)
    sock.connect(("api.oneme.ru", 443))
    seq = 0

    seq += 1
    sock.sendall(pack_frame(10, 0, seq, 6, {
        "userAgent": {
            "deviceType": "WEB", "locale": "ru", "deviceLocale": "ru",
            "osVersion": "Linux", "deviceName": "Firefox",
            "headerUserAgent": "Mozilla/5.0",
            "appVersion": "25.11.1",
            "screen": "1080x1920 1.0x",
            "timezone": "Asia/Yekaterinburg"
        },
        "deviceId": DEVICE_ID
    }))

    seq += 1
    sock.sendall(pack_frame(10, 0, seq, 19, {
        "interactive": True,
        "token": ACCESS_TOKEN,
        "chatsCount": 100, "chatsSync": 100,
        "contactsSync": 0, "presenceSync": 0, "draftsSync": 0
    }))

    for _ in range(10):
        f = recv_frame(sock)
        if f['opcode'] == 19 and f['cmd'] == 1:
            return sock, seq
    sock.close()
    raise RuntimeError("LOGIN failed")


# ─── Main ───

def main():
    # 1. Отправляем тестовое сообщение через WebSocket
    from websocket import create_connection
    print(f"📤 Отправляю: {MESSAGE_TEXT!r}")

    ws = create_connection("wss://ws-api.oneme.ru/websocket",
        header=["Origin: https://web.max.ru", "User-Agent: Mozilla/5.0"],
        timeout=10, sslopt={"context": _ssl_ctx})
    ws.settimeout(5)

    ws.send(json.dumps({"ver": 11, "cmd": 0, "seq": 1, "opcode": 6, "payload": {
        "userAgent": {"deviceType": "WEB", "locale": "ru", "deviceLocale": "ru",
          "osVersion": "Linux", "deviceName": "Firefox",
          "headerUserAgent": "Mozilla/5.0",
          "appVersion": "25.11.1",
          "screen": "1080x1920 1.0x",
          "timezone": "Asia/Yekaterinburg"},
        "deviceId": DEVICE_ID
    }}))
    ws.send(json.dumps({"ver": 11, "cmd": 0, "seq": 2, "opcode": 19, "payload": {
        "interactive": True, "token": ACCESS_TOKEN,
        "chatsCount": 100, "chatsSync": 100,
        "contactsSync": 0, "presenceSync": 0, "draftsSync": 0
    }}))

    for _ in range(10):
        r = json.loads(ws.recv())
        if r.get('cmd') == 1 and r.get('opcode') == 19:
            break

    seq = 3
    ws.send(json.dumps({"ver": 11, "cmd": 0, "seq": seq, "opcode": 64, "payload": {
        "chatId": CHAT_ID,
        "message": {"text": MESSAGE_TEXT, "cid": int(time.time() * 1000),
                    "elements": [], "attaches": []},
        "notify": True
    }}))

    msg_id = None
    for _ in range(10):
        r = json.loads(ws.recv())
        if r.get('cmd') == 1 and r.get('seq') == seq:
            msg_id = int(r['payload']['message']['id'])
            break
    ws.close()

    if not msg_id:
        print("❌ Не получил msg_id")
        return
    print(f"  ✅ msg_id={msg_id}")

    # 2. TCP DELETE (opcode 66)
    time.sleep(1)
    print(f"\n🔌 TCP MSG_DELETE (opcode 66) msg_id={msg_id} forMe=False...")

    sock, tcp_seq = tcp_connect()
    tcp_seq += 1
    sock.sendall(pack_frame(10, 0, tcp_seq, 66, {
        "chatId": CHAT_ID, "messageIds": [msg_id], "forMe": False
    }))

    sock.settimeout(5)
    responses = []
    for i in range(3):
        try:
            f = recv_frame(sock)
            responses.append((f['cmd'], f['opcode'], f['plen']))
        except socket.timeout:
            break
    sock.close()

    ack = any(cmd == 1 and op == 66 for cmd, op, _ in responses)
    print(f"  Ответы: {responses}")
    print(f"  ACK: {'✅' if ack else '❌'}")

    # 3. Проверка
    time.sleep(1.5)
    print(f"\n📡 Проверка: отправляю запрос истории...")

    ws = create_connection("wss://ws-api.oneme.ru/websocket",
        header=["Origin: https://web.max.ru", "User-Agent: Mozilla/5.0"],
        timeout=10, sslopt={"context": _ssl_ctx})
    ws.settimeout(5)
    ws.send(json.dumps({"ver": 11, "cmd": 0, "seq": 1, "opcode": 6, "payload": {
        "userAgent": {"deviceType": "WEB", "locale": "ru", "deviceLocale": "ru",
          "osVersion": "Linux", "deviceName": "Firefox",
          "headerUserAgent": "Mozilla/5.0",
          "appVersion": "25.11.1",
          "screen": "1080x1920 1.0x",
          "timezone": "Asia/Yekaterinburg"},
        "deviceId": DEVICE_ID
    }}))
    ws.send(json.dumps({"ver": 11, "cmd": 0, "seq": 2, "opcode": 19, "payload": {
        "interactive": True, "token": ACCESS_TOKEN,
        "chatsCount": 100, "chatsSync": 100,
        "contactsSync": 0, "presenceSync": 0, "draftsSync": 0
    }}))

    for _ in range(10):
        r = json.loads(ws.recv())
        if r.get('cmd') == 1 and r.get('opcode') == 19:
            break

    ws.send(json.dumps({"ver": 11, "cmd": 0, "seq": 3, "opcode": 49, "payload": {
        "chatId": CHAT_ID, "forward": 0, "backward": 10,
        "backwardTime": 0, "forwardTime": 0, "getChat": False,
        "from": int(time.time() * 1000),
        "getMessages": True, "interactive": False
    }}))

    found = False
    for _ in range(10):
        r = json.loads(ws.recv())
        if r.get('cmd') == 1 and r.get('opcode') == 49:
            for m in r['payload'].get('messages', []):
                mid = m.get('id')
                if str(mid) == str(msg_id) or mid == msg_id:
                    found = True
                    print(f"\n  id={mid} deleted={m.get('deleted')} "
                          f"text={str(m.get('text',''))[:50]!r}")
                    break
            break
    ws.close()

    if found:
        print("❌ Сообщение НЕ удалено")
    else:
        print(f"\n✅ Сообщение {msg_id} исчезло из истории!")
        print("   MSG_DELETE (opcode 66) работает!")

    # Не забываем удалить тестовое сообщение
    input("\nНажми Enter, чтобы удалить тестовое сообщение (opcode 66)...")
    sock, tcp_seq = tcp_connect()
    tcp_seq += 1
    sock.sendall(pack_frame(10, 0, tcp_seq, 66, {
        "chatId": CHAT_ID, "messageIds": [msg_id], "forMe": False
    }))
    sock.settimeout(2)
    try:
        f = recv_frame(sock)
        print(f"  Cleanup: cmd={f['cmd']} opcode={f['opcode']}")
    except:
        pass
    sock.close()
    print("✅ Удалено!")


if __name__ == "__main__":
    main()
