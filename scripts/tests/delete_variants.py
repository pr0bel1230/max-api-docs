#!/usr/bin/env python3
"""
Сканирование опкодов MAX API через TCP.
Отправляет DELETE-подобные запросы на диапазон опкодов и выводит ответы.
Полезно для идентификации назначения неизвестных опкодов.
"""
import json, os, ssl, struct, time, socket, msgpack, certifi

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN") or exit("❌ Укажи ACCESS_TOKEN")
DEVICE_ID = os.environ.get("DEVICE_ID") or exit("❌ Укажи DEVICE_ID")
CHAT_ID = int(os.environ.get("CHAT_ID", "7268926"))
MSG_ID = int(os.environ.get("MSG_ID", "0")) or exit("❌ Укажи MSG_ID (существующее сообщение)")

ctx = ssl.create_default_context(cafile=certifi.where())

def pack_frame(ver, cmd, seq, opcode, payload=None):
    pb = msgpack.packb(payload or {}, use_bin_type=True)
    return struct.pack(">BBHHI", ver, cmd, seq, opcode, len(pb)) + pb

def recv_exact(s, n):
    d = b""
    while len(d) < n:
        c = s.recv(n - len(d))
        if not c: raise ConnectionError("closed")
        d += c
    return d

def recv_frame(s):
    h = recv_exact(s, 10)
    _, cmd, _, op, pl = struct.unpack(">BBHHI", h)
    plen = pl & 0x00FFFFFF
    return {'cmd': cmd, 'opcode': op, 'plen': plen, 'payload': recv_exact(s, plen) if plen else b""}

def tcp_connect():
    s = socket.socket()
    sock = ctx.wrap_socket(s, server_hostname="api.oneme.ru")
    sock.settimeout(15); sock.connect(("api.oneme.ru", 443))
    seq = 0
    seq += 1; sock.sendall(pack_frame(10, 0, seq, 6, {
        "userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru",
          "osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0",
          "appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},
        "deviceId":DEVICE_ID}))
    seq += 1; sock.sendall(pack_frame(10, 0, seq, 19, {
        "interactive":True,"token":ACCESS_TOKEN,"chatsCount":100,"chatsSync":100,
        "contactsSync":0,"presenceSync":0,"draftsSync":0}))
    for _ in range(10):
        f = recv_frame(sock)
        if f['opcode']==19 and f['cmd']==1: return sock, seq
    sock.close(); raise RuntimeError("LOGIN failed")

print(f"Тестирование опкодов 65-92 с msg_id={MSG_ID}...\n")
print(f"{'Опкод':>6} | {'cmd':>3} | {'plen':>4} | Статус")
print("-" * 40)

for test_op in range(65, 93):
    time.sleep(0.2)
    try:
        sock, seq = tcp_connect()
        seq += 1
        sock.sendall(pack_frame(10, 0, seq, test_op, {
            "chatId": CHAT_ID, "messageIds": [MSG_ID], "forMe": False
        }))
        sock.settimeout(3)
        f = None
        for _ in range(2):
            try:
                f = recv_frame(sock)
                if f['cmd'] in (1, 3): break
            except: break
        if f:
            status = "✅" if f['cmd'] == 1 else "❌"
            print(f"{test_op:>6} | {f['cmd']:>3} | {f['plen']:>4} | {status}")
        else:
            print(f"{test_op:>6} |  - |    - | timeout")
        sock.close()
    except Exception as e:
        print(f"{test_op:>6} |  - |    - | error: {e}")

print("\nВажно: cmd=1 ≠ операция выполнена.")
print("Например, 65 всегда cmd=1, но это MSG_TYPING, а не MSG_DELETE.")
