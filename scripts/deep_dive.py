#!/usr/bin/env python3
"""
Deep investigation of interesting opcodes found in the scan.
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926

class S:
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
            if r: return r
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

def probe(label, op, pl):
    s = S()
    try:
        s.connect()
        resp = s.req(op, pl)
        if resp:
            print(f"  {resp.get('cmd')} {resp.get('opcode')}: {json.dumps(resp.get('payload',{}), ensure_ascii=False, indent=2)[:2000]}")
        else:
            print(f"  ⏰ timeout")
    except Exception as e:
        print(f"  💥 {e}")
    finally:
        s.close()

s = S()
s.connect()
print("🟢 CONNECTED")
print()

# ─── 1. OPCODE 79 — CALL HISTORY ─────────────────────────────────────
print("="*60)
print("OPCODE 79 — CALL HISTORY")
print("="*60)

# Basic — chat default
probe("79 basic", 79, {"chatId": SASHA})

# With count
s2 = S()
s2.connect()
r = s2.req(79, {"chatId": SASHA, "count": 20})
if r: print(f"79 count20: {json.dumps(r.get('payload',{}), ensure_ascii=False, indent=2)[:2000]}")
s2.close()

print()

# ─── 2. OPCODE 77 — operation ────────────────────────────────────────
print("="*60)
print("OPCODE 77 — needs 'operation'")
print("="*60)
probe("77 pin", 77, {"operation": "pin", "chatId": SASHA})
probe("77 archive", 77, {"operation": "archive", "chatId": SASHA})
probe("77 mute", 77, {"operation": "mute", "chatId": SASHA})
probe("77 read", 77, {"operation": "read", "chatId": SASHA})
print()

# ─── 3. OPCODE 5 — event ─────────────────────────────────────────────
print("="*60)
print("OPCODE 5 — needs 'event' (singular)")
print("="*60)
probe("5 typing", 5, {"event": "typing", "chatId": SASHA})
probe("5 read", 5, {"event": "read", "chatId": SASHA})
probe("5 online", 5, {"event": "online"})
print()

# ─── 4. OPCODE 69 — conversationId ──────────────────────────────────
print("="*60)
print("OPCODE 69 — needs 'conversationId' (call related)")
print("="*60)
probe("69 empty", 69, {"conversationId": "test", "chatId": SASHA})
# Get a real conversation ID from call history
s3 = S()
s3.connect()
r = s3.req(79, {"chatId": SASHA, "count": 5})
if r:
    history = (r.get("payload") or {}).get("history", [])
    for h in history:
        msgs = h.get("message", {}).get("attaches", [])
        for a in msgs:
            if a.get("_type") == "CALL":
                cid = a.get("conversationId")
                print(f"\n  Found CALL conversationId: {cid}")
                print(f"  Call details: {json.dumps(a, ensure_ascii=False, indent=2)[:500]}")
s3.close()
print()

# ─── 5. OPCODE 78 — isVideo ─────────────────────────────────────────
print("="*60)
print("OPCODE 78 — needs 'isVideo' (start call?)")
print("="*60)
probe("78 audio", 78, {"isVideo": False, "chatId": SASHA})
probe("78 video", 78, {"isVideo": True, "chatId": SASHA})
print()

# ─── 6. OPCODE 70 — needs 'text' ────────────────────────────────────
print("="*60)
print("OPCODE 70 — needs 'text'")
print("="*60)
probe("70 + chatId", 70, {"text": "test", "chatId": SASHA})
probe("70 + forward", 70, {"text": "test", "messageIds": [123]})
print()

# ─── 7. OPCODE 73 — needs 'count' ───────────────────────────────────
print("="*60)
print("OPCODE 73 — needs 'count'")
print("="*60)
probe("73 basic", 73, {"count": 10, "chatId": SASHA})
print()

# ─── 8. OPCODE 80 — needs 'count' ───────────────────────────────────
print("="*60)
print("OPCODE 80 — needs 'count'")
print("="*60)
probe("80 basic", 80, {"count": 10, "chatId": SASHA})
print()

# ─── 9. OPCODE 26 — preset ops alternative ──────────────────────────
print("="*60)
print("OPCODE 26 — enum values")
print("="*60)
for val in ["sticker", "gif", "emoji", "card", "file", "image", "video", "audio", "location", "contact", "reply", "forward", "link", "poll", "reaction"]:
    probe(f"26 {val}", 26, {"type": val})
print()

# ─── 10. OPCODE 75 ──────────────────────────────────────────────────
print("="*60)
print("OPCODE 75")
print("="*60)
probe("75 more", 75, {"chatId": SASHA, "count": 5})
probe("75 typing", 75, {"chatId": SASHA, "text": "test"})
print()

s.close()
print("\n✅ DONE")
