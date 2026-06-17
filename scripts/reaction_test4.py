#!/usr/bin/env /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""
Reaction test v4 — scan 93-99 with payloads, try different approaches.
Fresh WS for every probe.
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926

def one_req(op, pl):
    """Fresh connection, one request, return response."""
    ws = create_connection("wss://ws-api.oneme.ru/websocket",
        header=["Origin: https://web.max.ru"], timeout=15, sslopt={"context": _ssl_ctx})
    seq = 0
    # INIT
    seq += 1
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":seq,"opcode":6,"payload":{"userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},"deviceId":DID}}))
    seq += 1
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":seq,"opcode":19,"payload":{"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0}}))
    # Wait for LOGIN ack
    for _ in range(10):
        r = json.loads(ws.recv())
        if r.get("cmd") in (1,3) and r.get("opcode") == 19:
            break
    # Our request
    seq += 1
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":seq,"opcode":op,"payload":pl}))
    deadline = time.time() + 15
    result = None
    while time.time() < deadline:
        try:
            r = json.loads(ws.recv())
            if r.get("cmd") == 0: continue
            if r.get("seq") == seq:
                result = r
                break
        except:
            break
    ws.close()
    return result

def describe(r):
    if r is None: return "TIMEOUT"
    if r.get("cmd") == 1:
        p = r.get("payload", {})
        return f"ACK: {json.dumps(p, ensure_ascii=False)[:200]}"
    if r.get("cmd") == 3:
        e = r.get("payload", {})
        return f"ERR: {(e.get('message') or e.get('error') or str(e))[:200]}"
    return str(r)[:200]

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[1m"; N = "\033[0m"

now_ms = int(time.time() * 1000)
mid = 0  # placeholder message ID

print(f"{B}Reaction opcode hunt — targeted probes{N}\n")

# 1. Opcode 94 — postId
print(f"{B}1. Opcode 94 — postId{N}")
for post_id, label in [("test", "postId=test"), (str(mid), "postId=msgId"), (1, "postId=1")]:
    r = one_req(94, {"postId": post_id, "chatId": SASHA})
    print(f"  {label:<25s} → {describe(r)}")
    time.sleep(0.2)

# 2. Opcodes 88-89 with different fields
print(f"\n{B}2. Opcodes 88-89 — various{N}")
for op, pl, label in [
    (88, {"chatId": SASHA, "messageId": mid or 0, "fileId": "test"}, "88 fileId"),
    (88, {"fileId": "test"}, "88 only fileId"),
    (88, {"chatId": SASHA, "fileId": "test", "emoji": "👍"}, "88 file+emoji"),
    (89, {"chatId": SASHA, "link": "test"}, "89 link"),
    (89, {"chatId": SASHA, "link": "test", "pageId": 1}, "89 link+page"),
]:
    r = one_req(op, pl)
    print(f"  {label:<30s} → {describe(r)}")
    time.sleep(0.2)

# 3. Opcode 75 — reaction object with messageId string
print(f"\n{B}3. Opcodes 75 with msgIds as string/array{N}")
for pl, label in [
    ({"chatId": SASHA, "messageIds": [str(mid or "0")], "emoji": "👍"}, "messageIds array"),
    ({"chatId": SASHA, "messageId": str(mid or "0"), "reactions": ["👍", "❤️"]}, "reactions array"),
    ({"chatId": SASHA, "messageId": str(mid or "0"), "reaction": {"id": 1, "emoji": "👍"}}, "reaction w/ id"),
    ({"chatId": SASHA, "messageId": str(mid or "0"), "action": "add", "emoji": "👍"}, "action=add"),
]:
    r = one_req(75, pl)
    print(f"  {label:<40s} → {describe(r)}")
    time.sleep(0.2)

# 4. Try opcode 75 with actual messageId from history
print(f"\n{B}4. Opcode 75 with actual msgId + verify{N}")
ws = create_connection("wss://ws-api.oneme.ru/websocket",
    header=["Origin: https://web.max.ru"], timeout=15, sslopt={"context": _ssl_ctx})
seq = 0
seq += 1; ws.send(json.dumps({"ver":11,"cmd":0,"seq":seq,"opcode":6,"payload":{"userAgent":{"deviceType":"WEB"},"deviceId":DID}}))
seq += 1; ws.send(json.dumps({"ver":11,"cmd":0,"seq":seq,"opcode":19,"payload":{"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0}}))
for _ in range(10):
    r = json.loads(ws.recv())
    if r.get("opcode") == 19: break

def req(ws, seq, op, pl):
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":seq,"opcode":op,"payload":pl}))
    d = time.time()+15
    while time.time()<d:
        r = json.loads(ws.recv())
        if r.get("cmd")==0: continue
        if r.get("seq")==seq: return r
    return None

# Get a real message
seq += 1
r = req(ws, seq, 49, {"chatId": SASHA, "backward": 20, "getMessages": True, "from": int(time.time()*1000)})
msgs = r.get("payload", {}).get("messages", [])
text_msgs = [m for m in msgs if m.get("text","").strip() and m.get("type")=="USER"]
if text_msgs:
    real_id = text_msgs[0].get("id")
    print(f"  Using msgId={real_id} \"{text_msgs[0].get('text','')[:50]}\"")

    # BEFORE
    seq += 1; r = req(ws, seq, 71, {"chatId": SASHA, "messageIds": [real_id]})
    before = r.get("payload",{}).get("messages",[{}])[0].get("reactionInfo",{})
    print(f"  BEFORE: {json.dumps(before, ensure_ascii=False)[:200]}")

    # Try 75 with real msgId, different "reaction" field format
    format_tests = [
        ({"chatId": SASHA, "messageId": real_id, "reaction": "like"}, "reaction=like"),
        ({"chatId": SASHA, "messageId": real_id, "emojiId": 1}, "emojiId=1"),
        ({"chatId": SASHA, "messageId": real_id, "reactionId": "like"}, "reactionId=like"),
        ({"chatId": SASHA, "messageId": real_id, "reactionId": "like", "emoji": "👍"}, "reactionId+emoji"),
        ({"chatId": SASHA, "messageId": real_id, "addReaction": "👍"}, "addReaction"),
        ({"chatId": SASHA, "messageId": real_id, "reactionType": "LIKE", "emoji": "❤️"}, "type+emoji"),
        ({"chatId": SASHA, "messageId": real_id, "type": "REACTION", "emoji": "👍"}, "type=REACTION"),
        ({"chatId": SASHA, "messageId": real_id, "updateType": "REACTION", "emoji": "👍"}, "updateType"),
    ]
    for pl, label in format_tests:
        seq += 1
        r = req(ws, seq, 75, pl)
        print(f"  {label:<25s} → {describe(r)}")
        time.sleep(0.3)

    # AFTER
    seq += 1; r = req(ws, seq, 71, {"chatId": SASHA, "messageIds": [real_id]})
    after = r.get("payload",{}).get("messages",[{}])[0].get("reactionInfo",{})
    print(f"\n  AFTER: {json.dumps(after, ensure_ascii=False)[:300]}")
    if before != after:
        print(f"  {G}✅ CHANGED!{N}")
    else:
        print(f"  {Y}❌ Same{N}")

ws.close()

# 5. Try other opcodes around chat operations that might handle reactions
print(f"\n{B}5. Various opcodes with reaction-like payloads{N}")
for op, pl, label in [
    (55, {"chatId": SASHA, "messageId": real_id, "emoji": "👍"}, "op55"),
    (56, {"chatId": SASHA, "messageId": real_id or 0, "emoji": "👍"}, "op56"),
    (57, {"chatId": SASHA, "messageId": real_id or 0, "emoji": "👍"}, "op57"),
    (58, {"chatId": SASHA, "messageId": real_id or 0, "emoji": "👍"}, "op58"),
    (59, {"chatId": SASHA, "messageId": real_id or 0, "emoji": "👍"}, "op59"),
    (60, {"chatId": SASHA, "messageId": real_id or 0, "emoji": "👍"}, "op60"),
    (61, {"chatId": SASHA, "messageId": real_id or 0, "emoji": "👍"}, "op61"),
    (62, {"chatId": SASHA, "messageId": real_id or 0, "emoji": "👍"}, "op62"),
    (63, {"chatId": SASHA, "messageId": real_id or 0, "emoji": "👍"}, "op63"),
]:
    r = one_req(op, pl)
    if r and r.get("cmd") == 1:
        print(f"  {label:<15s} → {G}ACK{N}: {describe(r)}")
    elif r and r.get("cmd") == 3:
        e = r.get("payload", {})
        msg = (e.get("message") or e.get("error") or str(e))[:150]
        print(f"  {label:<15s} → {R}ERR{N}: {msg}")
    time.sleep(0.1)

print(f"\n{B}DONE{N}")
