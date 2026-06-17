#!/usr/bin/env /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""
Deep dive round 2:
- Opcode 272 (chat folders)
- Opcode 92 (MSG_DELETE_RANGE with endTime)
- Opcode 75 (reaction candidate)
- Opcode 200 (timestamp), 201 (users)
- Opcode 100, 103 (new finds)
- Opcodes requiring NEW session (101, 115, 116)
- Opcode 86 (show param)
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926
MY_USER_ID = 3260455

G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; C = "\033[96m"; B = "\033[1m"; N = "\033[0m"

class Session:
    def __init__(self):
        self.ws, self.seq, self.user_id = None, 0, None

    def connect_raw(self):
        """Just open WS, don't INIT/LOGIN."""
        self.ws = create_connection("wss://ws-api.oneme.ru/websocket",
            header=["Origin: https://web.max.ru", "User-Agent: Mozilla/5.0"],
            timeout=15, sslopt={"context": _ssl_ctx})
        return True

    def connect(self):
        self.connect_raw()
        self.seq += 1
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":6,"payload":{"userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},"deviceId":DID}}))
        self.seq += 1
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":19,"payload":{"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0}}))
        for _ in range(10):
            r = self._r(10)
            if r and r.get("cmd") == 1 and r.get("opcode") == 19:
                self.user_id = r.get("payload", {}).get("userId", MY_USER_ID)
                return True
            if r and r.get("cmd") == 3 and r.get("opcode") == 19:
                print(f"  {R}LOGIN FAILED: {r.get('payload', {}).get('message', '')}{N}")
                return False
        return False

    def req(self, op, pl, t=20):
        self.seq += 1
        rid = self.seq
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":rid,"opcode":op,"payload":pl}))
        d = time.time() + t
        while time.time() < d:
            r = self._r(8)
            if r:
                if r.get("cmd") == 0: continue
                if r.get("seq") == rid: return r
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

def probe(op, pl, t=20):
    s = Session()
    try:
        if op in (101, 115, 116, 118):
            s.connect_raw()
        else:
            if not s.connect(): return None
        return s.req(op, pl, t)
    except: return None
    finally: s.close()

def acr(op, resp):
    """Pretty-print response."""
    if resp is None: return f"{Y}TIMEOUT{N}"
    cmd = resp.get("cmd")
    if cmd == 1:
        pl = resp.get("payload", {})
        s = json.dumps(pl, ensure_ascii=False, indent=2) if pl else "null"
        if len(s) > 800: s = s[:797] + "..."
        return f"{G}ACK{N}\n{indent(s, 4)}"
    elif cmd == 3:
        err = resp.get("payload", {})
        msg = (err.get("message") or err.get("error") or str(err))[:300]
        return f"{R}ERR{N} {msg}"
    return f"{Y}cmd={cmd}{N} {str(resp)[:200]}"

def indent(s, n):
    return "\n".join(" " * n + l if l.strip() else l for l in s.split("\n"))

def hr(t="───"):
    print(f"\n{C}{'─'*50}{N}")
    print(f"{B}{C}{t}{N}")

# ────────────────────────────────────────────────────────
print(f"{B}{C}🔬 DEEP DIVE ROUND 2{N}\n")

# 0. Verify
s = Session()
if not s.connect():
    print(f"{R}❌ Токен мёртв{N}"); exit(1)
print(f"✅ userId={s.user_id}")
s.close()

# ────────────────────────────────────────────────────────
# OPCODE 272 — Chat folders
# ────────────────────────────────────────────────────────
hr("OPCODE 272 — CHAT FOLDERS")

# Try different payloads
for pl, label in [
    ({}, "empty"),
    ({"chatId": SASHA}, "with chatId"),
]:
    r = probe(272, pl)
    print(f"\n  {B}{label}:{N} {acr(272, r)}")

# Full exploration of 272 response
r = probe(272, {})
if r and r.get("cmd") == 1:
    pl = r.get("payload", {})
    print(f"\n  {B}Детальный разбор 272:{N}")
    print(f"    folderSync: {pl.get('folderSync')}")
    print(f"    foldersOrder: {pl.get('foldersOrder')}")
    for f in pl.get("folders", []):
        print(f"    Папка: id={f.get('id')}, title={f.get('title')}")
        print(f"      include={f.get('include')}")
        print(f"      filters={f.get('filters')}")
        if "exclude" in f:
            print(f"      exclude={f.get('exclude')}")
        if "elements" in f:
            print(f"      elements_count={len(f.get('elements', []))}")

# ────────────────────────────────────────────────────────
# OPCODE 92 — MSG_DELETE_RANGE with endTime
# ────────────────────────────────────────────────────────
hr("OPCODE 92 — MSG_DELETE_RANGE")

now = int(time.time() * 1000)
for pl, label in [
    ({"chatId": SASHA, "endTime": now}, "only endTime"),
    ({"chatId": SASHA, "endTime": now, "fromId": 0}, "endTime + fromId"),
    ({"chatId": SASHA, "endTime": now, "fromId": 0, "forMe": True}, "full + forMe"),
    ({"chatId": SASHA, "endTime": now, "forMe": True}, "endTime + forMe"),
]:
    r = probe(92, pl)
    print(f"  {label:<30s} → {acr(92, r)}")

# ────────────────────────────────────────────────────────
# OPCODE 75 — Reaction candidate
# ────────────────────────────────────────────────────────
hr("OPCODE 75 — REACTION CANDIDATE")

# Get real message first
s = Session()
s.connect()
hist = s.req(49, {"chatId": SASHA, "backward": 10, "getMessages": True})
msg_id = None
my_msg_id = None
if hist and hist.get("cmd") == 1:
    msgs = hist.get("payload", {}).get("messages", [])
    print(f"  Сообщений в истории: {len(msgs)}")
    for m in msgs[:5]:
        print(f"    msgId={m.get('id')} sender={m.get('sender')} text=\"{m.get('text','')[:60]}\"")
        if not msg_id:
            msg_id = m.get("id")
        if m.get("sender") == s.user_id and not my_msg_id:
            my_msg_id = m.get("id")
s.close()

if msg_id:
    print(f"\n  Использую messageId={msg_id}, my_messageId={my_msg_id}")

    # Test 75 with real messageId
    for pl, label in [
        ({"chatId": SASHA, "messageId": msg_id, "emoji": "👍"}, "emoji string"),
        ({"chatId": SASHA, "messageId": msg_id, "reactionType": "LIKE"}, "reactionType LIKE"),
        ({"chatId": SASHA, "messageId": msg_id, "reactionType": "DISLIKE"}, "reactionType DISLIKE"),
        ({"chatId": SASHA, "messageId": msg_id, "reaction": {"type": "emoji", "content": "❤️"}}, "reaction object"),
        ({"chatId": SASHA, "messageId": msg_id, "action": "add", "emoji": "👍"}, "add action"),
        ({"chatId": SASHA, "messageId": msg_id, "reactionId": "like", "action": "add"}, "reactionId add"),
    ]:
        r = probe(75, pl)
        c = acr(75, r)
        print(f"  [{c[:5]}] {label:<30s} → {c}")

# ────────────────────────────────────────────────────────
# OPCODE 200 — timestamp/stat
# ────────────────────────────────────────────────────────
hr("OPCODE 200 — TIMESTAMP/STAT")

now = int(time.time() * 1000)
for pl, label in [
    ({}, "empty"),
    ({"timestamp": now}, "with timestamp"),
]:
    r = probe(200, pl)
    print(f"  {label:<20s} → {acr(200, r)}")

# ────────────────────────────────────────────────────────
# OPCODE 201 — users[]
# ────────────────────────────────────────────────────────
hr("OPCODE 201 — USERS")

for pl, label in [
    ({}, "empty"),
    ({"userIds": [MY_USER_ID]}, "my userId"),
    ({"userIds": [6236697]}, "Sasha's userId"),
]:
    r = probe(201, pl)
    print(f"  {label:<20s} → {acr(201, r)}")

# ────────────────────────────────────────────────────────
# OPCODE 100 — what is it?
# ────────────────────────────────────────────────────────
hr("OPCODE 100 — ???")

for pl, label in [
    ({}, "empty"),
    ({"chatId": SASHA}, "chatId"),
    ({"count": 10}, "count"),
    ({"marker": 0}, "marker"),
    ({"userId": MY_USER_ID}, "userId"),
]:
    r = probe(100, pl)
    print(f"  {label:<20s} → {acr(100, r)}")

# ────────────────────────────────────────────────────────
# OPCODE 103 — ???
# ────────────────────────────────────────────────────────
hr("OPCODE 103 — ???")

for pl, label in [
    ({}, "empty"),
    ({"chatId": SASHA}, "chatId"),
    ({"count": 10}, "count"),
]:
    r = probe(103, pl)
    print(f"  {label:<20s} → {acr(103, r)}")

# ────────────────────────────────────────────────────────
# OPCODES 101, 115, 116 — NEW SESSION (before LOGIN)
# ────────────────────────────────────────────────────────
hr("OPCODES 101, 115, 116 — PRE-LOGIN")

for op, pl in [(101, {}), (115, {}), (116, {}), (118, {})]:
    s = Session()
    s.connect_raw()
    r = s.req(op, pl)
    print(f"  [{op:3d}] (pre-login) → {acr(op, r)}")
    s.close()

# Also try some with just userId after login
for op in [101, 115, 116]:
    r = probe(op, {"userId": MY_USER_ID})
    print(f"  [{op:3d}] (post-login w/ userId) → {acr(op, r)}")

# ────────────────────────────────────────────────────────
# OPCODE 86 — needs show param
# ────────────────────────────────────────────────────────
hr("OPCODE 86 — SHOW?")

for pl, label in [
    ({"chatId": SASHA, "show": "all"}, "show=all"),
    ({"chatId": SASHA, "show": "active"}, "show=active"),
    ({"chatId": SASHA, "show": "archived"}, "show=archived"),
    ({"show": "all"}, "show=all no chatId"),
    ({"show": "all", "count": 50}, "show=all count=50"),
]:
    r = probe(86, pl)
    print(f"  {label:<25s} → {acr(86, r)}")

# ────────────────────────────────────────────────────────
# OPCODE 81 — another IMAGE_UPLOAD_URL?
# ────────────────────────────────────────────────────────
hr("OPCODE 81 — IMAGE_UPLOAD variant")

for pl, label in [
    ({}, "empty"),
    ({"count": 1}, "count=1"),
    ({"count": 3}, "count=3"),
    ({"chatId": SASHA}, "with chatId"),
]:
    r = probe(81, pl)
    print(f"  {label:<20s} → {acr(81, r)}")

# ────────────────────────────────────────────────────────
# OPCODE 90 — not accessible
# ────────────────────────────────────────────────────────
hr("OPCODE 90 — 'chat not accessible'")

for pl, label in [
    ({"chatId": SASHA}, "chatId"),
    ({}, "empty"),
    ({"chatId": SASHA, "count": 10}, "with count"),
]:
    r = probe(90, pl)
    print(f"  {label:<20s} → {acr(90, r)}")

print(f"\n{B}{C}🏁 DONE{N}")
