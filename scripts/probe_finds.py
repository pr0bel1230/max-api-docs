#!/usr/bin/env /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""
Probe the most interesting new finds:
- Opcode 61: chat info
- Opcode 92: chat by time range (vs MSG_DELETE_RANGE?)
- Opcode 55: ACK with {}
- Opcode 86: show chats
- Opcode 81: iusmile image upload
- Try 92 with messageIds array
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926

G="\033[92m";Y="\033[93m";R="\033[91m";C="\033[96m";B="\033[1m";N="\033[0m"

def fresh_connect():
    ws = create_connection("wss://ws-api.oneme.ru/websocket",
        header=["Origin: https://web.max.ru"], timeout=15, sslopt={"context":_ssl_ctx})
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":1,"opcode":6,"payload":{"userAgent":{"deviceType":"WEB"},"deviceId":DID}}))
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":2,"opcode":19,"payload":{"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0}}))
    for _ in range(10):
        r = json.loads(ws.recv())
        if r.get("opcode")==19 and r.get("cmd")==1:
            return ws
    ws.close()
    return None

def req(ws, seq, op, pl):
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":seq,"opcode":op,"payload":pl}))
    d = time.time()+15
    while time.time()<d:
        r = json.loads(ws.recv())
        if r.get("cmd")==0: continue
        if r.get("seq")==seq: return r
    return None

def desc(r):
    if r is None: return f"{Y}TIMEOUT{N}"
    if r.get("cmd")==1:
        p = r.get("payload",{})
        j = json.dumps(p, ensure_ascii=False, indent=2) if p else "null"
        if len(j) > 1000: j = j[:997] + "..."
        return f"{G}ACK{N}\n" + "\n".join("  " + line for line in j.split("\n"))
    if r.get("cmd")==3:
        e = r.get("payload",{})
        return f"{R}ERR{N} {(e.get('message') or e.get('error') or str(e))[:200]}"
    return str(r)[:200]

NOW_MS = int(time.time()*1000)

# ──────────────────────────────────────────────────
# 1. OPCODE 61 — chat info
# ──────────────────────────────────────────────────
print(f"{B}1. OPCODE 61 — chat info{N}")
ws = fresh_connect()
r = req(ws, 3, 61, {"chatId": SASHA, "emoji": "👍"})  # original reaction candidate
print(f"emoji with chatId: {desc(r)}")

r = req(ws, 4, 61, {"chatId": SASHA})
print(f"just chatId: {desc(r)}")

r = req(ws, 5, 61, {})
print(f"empty: {desc(r)}")

# Extract and display chat info fields
r = req(ws, 6, 61, {"chatId": SASHA})
if r and r.get("cmd")==1:
    chat = r.get("payload",{}).get("chat",{})
    print(f"\n  Chat info from 61:")
    print(f"    type={chat.get('type')} status={chat.get('status')}")
    print(f"    owner={chat.get('owner')} modified={chat.get('modified')}")
    print(f"    participants: {json.dumps(chat.get('participants',{}), ensure_ascii=False)[:200]}")
    print(f"    lastMessage: \"{chat.get('lastMessage',{}).get('text','')[:60]}\"")
ws.close()

# ──────────────────────────────────────────────────
# 2. OPCODE 92 — time range / delete range?
# ──────────────────────────────────────────────────
print(f"\n{B}2. OPCODE 92 — time range vs delete{N}")
ws = fresh_connect()

# Try with messageIds like MSG_DELETE
r = req(ws, 3, 92, {"chatId": SASHA, "messageIds": ["116483269189784770"], "forMe": True})
print(f"messageIds + forMe: {desc(r)}")

# Try with startTime in the past
r = req(ws, 4, 92, {"chatId": SASHA, "startTime": int(NOW_MS-86400000), "endTime": NOW_MS})
print(f"last 24h range: {desc(r)}")

# Try startTime=0 (beginning of time) to now
r = req(ws, 5, 92, {"chatId": SASHA, "startTime": 1750656617842, "endTime": NOW_MS})
print(f"full range: {desc(r)}")
ws.close()

# ──────────────────────────────────────────────────
# 3. OPCODE 55 — what is it?
# ──────────────────────────────────────────────────
print(f"\n{B}3. OPCODE 55 — mystery (ACKs with {{}}){N}")
for pl, label in [
    ({}, "empty"),
    ({"chatId": SASHA}, "chatId"),
    ({"count": 10}, "count"),
    ({"marker": 0}, "marker"),
    ({"query": "test"}, "query"),
    ({"userId": 3260455}, "userId"),
]:
    ws = fresh_connect()
    r = req(ws, 3, 55, pl)
    print(f"  {label:<15s} → {desc(r)}")
    ws.close()
    time.sleep(0.2)

# ──────────────────────────────────────────────────
# 4. OPCODE 86 — show chats
# ──────────────────────────────────────────────────
print(f"\n{B}4. OPCODE 86 — show chats (boolean){N}")
ws = fresh_connect()
for show_flag in [True, False]:
    r = req(ws, 3, 86, {"chatId": SASHA, "show": show_flag})
    print(f"  show={str(show_flag):<6s} → {desc(r)}")

# Try with folder-related payload
r = req(ws, 4, 86, {"show": True, "chatId": SASHA, "count": 100})
print(f"  show=True+count: {desc(r)}")
ws.close()

# ──────────────────────────────────────────────────
# 5. OPCODE 81 vs 80 — image upload URLs comparison
# ──────────────────────────────────────────────────
print(f"\n{B}5. OPCODE 80 vs 81 — image upload endpoints{N}")
for op, label in [(80, "iu.oneme.ru"), (81, "iusmile.oneme.ru")]:
    ws = fresh_connect()
    r = req(ws, 3, op, {"count": 1})
    if r and r.get("cmd")==1:
        url = r.get("payload",{}).get("url","")
        print(f"  [{op}] {label}: {url[:120]}...")
    else:
        print(f"  [{op}] {label}: {desc(r)}")
    ws.close()

# ──────────────────────────────────────────────────
# 6. OPCODE 201 — users (try POST-like payload)
# ──────────────────────────────────────────────────
print(f"\n{B}6. OPCODE 201 — users (alternative payloads){N}")
for pl, label in [
    ({"userIds": [3260455]}, "userIds=[int]"),
    ({"ids": ["3260455"]}, "ids=[str]"),
    ({"users": [{"id": 3260455}]}, "users=[obj]"),
    ({"userId": 3260455, "fields": ["name", "avatar"]}, "userId+fields"),
    ({"userId": "3260455"}, "userId=str"),
]:
    ws = fresh_connect()
    r = req(ws, 3, 201, pl)
    if r and r.get("cmd")==1:
        users = r.get("payload",{}).get("users",[])
        print(f"  {label:<25s} → ACK users={users}")
    else:
        print(f"  {label:<25s} → {desc(r)}")
    ws.close()
    time.sleep(0.2)

print(f"\n{G}{B}DONE{N}")
