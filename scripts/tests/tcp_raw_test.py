#!/usr/bin/env python3
"""
Снятие raw-дампов TCP протокола MAX после INIT и LOGIN.
Полезно для отладки и исследования структуры ответов.
"""
import json, os, ssl, struct, socket, msgpack, certifi

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN") or exit("❌ Укажи ACCESS_TOKEN")
DEVICE_ID = os.environ.get("DEVICE_ID") or exit("❌ Укажи DEVICE_ID")

ctx = ssl.create_default_context(cafile=certifi.where())
sock = ctx.wrap_socket(socket.socket(), server_hostname="api.oneme.ru")
sock.settimeout(15)
sock.connect(("api.oneme.ru", 443))

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
    payload = recv_exact(s, plen) if plen else b""
    return {'cmd': cmd, 'opcode': op, 'plen': plen, 'payload': payload}

# INIT
seq = 1
sock.sendall(pack_frame(10, 0, seq, 6, {
    "userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru",
      "osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0",
      "appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},
    "deviceId":DEVICE_ID
}))
f = recv_frame(sock)
print(f"INIT: cmd={f['cmd']} opcode={f['opcode']} len={f['plen']}")
print(f"  raw ({len(f['payload'])}): {f['payload'][:64].hex()}")

# LOGIN
seq = 2
sock.sendall(pack_frame(10, 0, seq, 19, {
    "interactive":True,"token":ACCESS_TOKEN,
    "chatsCount":100,"chatsSync":100,
    "contactsSync":0,"presenceSync":0,"draftsSync":0
}))
f = recv_frame(sock)
print(f"\nLOGIN: cmd={f['cmd']} opcode={f['opcode']} len={f['plen']}")
print(f"  raw ({len(f['payload'])}): {f['payload'][:64].hex()}")
sock.close()
