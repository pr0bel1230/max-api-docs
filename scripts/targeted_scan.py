#!/usr/bin/env python3
"""
Targeted investigation of interesting MAX opcodes.
Does ONE clean connection per test to avoid drop issues.
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926

class Session:
    def __init__(self):
        self.ws, self.seq = None, 0

    def connect(self):
        self.ws = create_connection("wss://ws-api.oneme.ru/websocket",
            header=["Origin: https://web.max.ru", "User-Agent: Mozilla/5.0"],
            timeout=10, sslopt={"context": _ssl_ctx})
        self.seq += 1
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":6,"payload":{"userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},"deviceId":DID}}))
        self.seq += 1
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":19,"payload":{"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0}}))
        for _ in range(8):
            r = self._r(10)
            if r and r.get("cmd")==1 and r.get("opcode")==19: return

    def req(self, op, pl, t=15):
        self.seq += 1
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":op,"payload":pl}))
        d = time.time()+t
        while time.time()<d:
            r = self._r(5)
            if r: return r  # return full response
        return None

    def _r(self, t=5):
        if not self.ws: return None
        self.ws.settimeout(t)
        try: r = self.ws.recv(); return json.loads(r) if r else None
        except: return None

    def close(self):
        if self.ws:
            try: self.ws.close()
            except: pass

def probe(opcode, payload, label=""):
    """One clean connection, one request."""
    s = Session()
    try:
        s.connect()
        resp = s.req(opcode, payload)
        if resp:
            cmd = resp.get("cmd")
            if cmd == 1:
                pl = resp.get("payload", {})
                print(f"  ✅ opcode {opcode:3d}: ACK: {json.dumps(pl, ensure_ascii=False)[:500]}")
                return pl
            elif cmd == 3:
                err = resp.get("payload", {})
                txt = err.get("message", str(err)[:200]) if isinstance(err, dict) else str(err)[:200]
                print(f"  ❌ opcode {opcode:3d}: ERROR: {txt}")
                return err
        else:
            print(f"  ⏰ opcode {opcode:3d}: timeout (no response)")
            return None
    except Exception as e:
        print(f"  💥 opcode {opcode:3d}: {type(e).__name__}: {str(e)[:100]}")
        return None
    finally:
        s.close()

# ─── Targeted investigations ───────────────────────────────────────────

print("🎯 TARGETED OPCODE INVESTIGATION\n")

# 1. Opcode 25 — presetAvatars
print("1️⃣  OPCODE 25 — presetAvatars")
probe(25, {})
probe(25, {"count": 10})
probe(25, {"offset": 0, "count": 20})
print()

# 2. Opcode 5 — events subscription?
print("2️⃣  OPCODE 5 — events?")
probe(5, {"events": [{"type": "typing", "chatId": SASHA}]})
probe(5, {"events": [{"type": "*"}]})
print()

# 3. Opcode 8 — binary expected? Try different payloads
print("3️⃣  OPCODE 8 — binary?")
probe(8, {})
probe(8, {"text": "test"})
probe(8, {"chatId": SASHA, "text": "test"})
print()

# 4. Opcodes 17/23 — NEW session ops (pre-connection)
print("4️⃣  PRE-AUTH OPS (separate session)")
s = Session()
s.ws = create_connection("wss://ws-api.oneme.ru/websocket",
    header=["Origin: https://web.max.ru", "User-Agent: Mozilla/5.0"],
    timeout=10, sslopt={"context": _ssl_ctx})
s.seq = 0
for op in [17, 18, 23, 24]:
    s.seq += 1
    pl = {}
    if op == 23: pl = {"ping": int(time.time()*1000)}
    try:
        s.ws.send(json.dumps({"ver":11,"cmd":0,"seq":s.seq,"opcode":op,"payload":pl}))
        s.ws.settimeout(8)
        raw = s.ws.recv()
        if raw: print(f"  🔵 opcode {op:3d}: {json.loads(raw)}")
        else: print(f"  ⏰ opcode {op:3d}: no response")
    except Exception as e:
        print(f"  💥 opcode {op:3d}: {e}")
s.close()
print()

# 5. Opcode 26 — presetAvatars variant?
print("5️⃣  OPCODE 26 — other preset ops?")
probe(26, {})
probe(26, {"type": "avatar"})
probe(26, {"presetId": 1})
print()

# 6. Opcode 69, 73, 75-86 — chat/group ops?
print("6️⃣  MID-RANGE OPS")
for op in [69, 70, 73, 75, 76, 77, 78, 79, 80]:
    probe(op, {"chatId": SASHA})
print()

# Try opcode 1 which got empty ACK
print("7️⃣  OPCODE 1 — ping?")
probe(1, {})
probe(1, {"ping": int(time.time()*1000)})
print()
