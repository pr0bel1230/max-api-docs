#!/usr/bin/env python3
"""
Final targeted probes for a few remaining unknowns.
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA, ME = 7268926, 3260455

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
    ss = S()
    try:
        ss.connect()
        resp = ss.req(op, pl)
        if resp:
            print(f"[{label}] cmd={resp.get('cmd')} seq={resp.get('seq')}")
            print(f"  {json.dumps(resp.get('payload',{}), ensure_ascii=False, indent=2)[:1000]}")
        else:
            print(f"[{label}] ⏰ timeout")
    except Exception as e:
        print(f"[{label}] 💥 {e}")
    finally:
        ss.close()
    print()

# ─── 1. Opcode 70: Search messages? ────────────────────────────────
print("="*60)
print("OPCODE 70 — text search")
print("="*60)
probe("70 empty", 70, {"text": "привет"})
probe("70 chat scoped", 70, {"text": "привет", "chatId": SASHA})
probe("70 count", 70, {"text": "а", "chatId": SASHA, "count": 5})
probe("70 with marker", 70, {"text": "а", "count": 3, "marker": 0})

# ─── 2. Opcode 73: Global search? ─────────────────────────────────
print("="*60)
print("OPCODE 73 — needs query")
print("="*60)
probe("73 basic", 73, {"query": "привет", "count": 5})
probe("73 chat", 73, {"query": "привет", "count": 5, "chatId": SASHA})

# ─── 3. Opcode 77: Chat operation with userIds ────────────────────
print("="*60)
print("OPCODE 77 — chat ops with userIds")
print("="*60)
probe("77 pin+userIds", 77, {"operation": "pin", "chatId": SASHA, "userIds": [ME]})
probe("77 mute+userIds", 77, {"operation": "mute", "chatId": SASHA, "userIds": [ME]})
probe("77 archive+userIds", 77, {"operation": "archive", "chatId": SASHA, "userIds": [ME]})
probe("77 read+userIds", 77, {"operation": "read", "chatId": SASHA, "userIds": [ME]})

# ─── 4. Opcode 69: Call edit with real conversationId ─────────────
print("="*60)
print("OPCODE 69 — CALL_EDIT (mute)")
print("="*60)
# Get a real conversation ID
scan = S()
scan.connect()
r = scan.req(79, {"chatId": SASHA, "count": 1})
if r:
    h = (r.get("payload") or {}).get("history", [])
    if h:
        cid = h[0]["message"]["attaches"][0]["conversationId"]
        print(f"  Using conversationId: {cid}")
        probe("69 mute_audio", 69, {"conversationId": cid, "muteAudio": True})
        probe("69 mute_video", 69, {"conversationId": cid, "muteVideo": True})
        probe("69 end", 69, {"conversationId": cid, "closed": True})
scan.close()

# ─── 5. Opcode 78: Start call with real data ──────────────────────
print("="*60)
print("OPCODE 78 — start call?")
print("="*60)
probe("78 call_audio", 78, {"conversationId": "test-123", "isVideo": False, "chatId": SASHA})

# ─── 6. Opcode 80 with different payloads ─────────────────────────
print("="*60)
print("OPCODE 80 — upload URL")
print("="*60)
probe("80 count", 80, {"count": 1})
probe("80 count+photoId", 80, {"count": 1, "photoIds": ["test"]})

# ─── 7. Opcode 26 — sticker pagination ────────────────────────────
print("="*60)
print("OPCODE 26 — GET_PRESETS (pagination)")
print("="*60)
probe("26 sticker+marker", 26, {"type": "sticker", "marker": 0, "count": 10})
probe("26 emoji+marker", 26, {"type": "emoji", "marker": 0, "count": 10})
probe("26 reaction+marker", 26, {"type": "reaction", "marker": 0, "count": 10})
