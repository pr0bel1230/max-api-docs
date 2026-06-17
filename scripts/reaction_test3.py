#!/usr/bin/env /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""
Reaction test v3 — try reaction via MSG_SEND with special attach,
and try opcode 75 with preset-based reaction IDs.
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926

def connect():
    ws = create_connection("wss://ws-api.oneme.ru/websocket",
        header=["Origin: https://web.max.ru"], timeout=15, sslopt={"context": _ssl_ctx})
    return ws

def req(ws, seq, op, pl):
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":seq,"opcode":op,"payload":pl}))
    deadline = time.time() + 15
    while time.time() < deadline:
        r = json.loads(ws.recv())
        if r.get("cmd") == 0: continue
        if r.get("seq") == seq: return r
    return None

def init(ws, seq_start=0):
    s = seq_start
    req(ws, s+1, 6, {"userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},"deviceId":DID})
    r = req(ws, s+2, 19, {"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0})
    return r, s+2

# ── PHASE 1: Check preset structure ──
print("PHASE 1: GET_PRESETS (26) reaction types")
ws = connect()
init(ws, 0)

# Get reaction presets
r = req(ws, 3, 26, {"type": "reaction", "marker": 0, "count": 50})
print(f"  reactions: {json.dumps(r.get('payload',{}), ensure_ascii=False)[:500]}")

# Get emoji presets
r = req(ws, 4, 26, {"type": "emoji", "marker": 0, "count": 50})
print(f"  emojis: {json.dumps(r.get('payload',{}), ensure_ascii=False)[:500]}")

# Get sticker presets
r = req(ws, 5, 26, {"type": "sticker", "marker": 0, "count": 50})
print(f"  stickers: {json.dumps(r.get('payload',{}), ensure_ascii=False)[:500]}")

ws.close()

# ── PHASE 2: Try reactions via MSG_SEND ──
print("\nPHASE 2: Reaction via MSG_SEND (64) special attaches")
ws = connect()
init(ws, 10)
now_ms = int(time.time() * 1000)

# Get a target message
r = req(ws, 13, 49, {"chatId": SASHA, "backward": 20, "getMessages": True, "from": now_ms})
msgs = r.get("payload", {}).get("messages", [])
text_msgs = [m for m in msgs if m.get("text","").strip() and m.get("type")=="USER"]
test_id = None
if text_msgs:
    test_id = text_msgs[0].get("id")
    print(f"  Target msg: id={test_id} \"{text_msgs[0].get('text','')[:50]}\"")

if test_id:
    # Try sending a reaction as a special attach
    reaction_attaches = [
        {"_type": "REACTION", "messageId": test_id, "emoji": "👍"},
        {"type": "REACTION", "messageId": test_id, "emoji": "👍"},
        {"_type": "REACTION", "messageId": test_id, "reactionType": "like"},
        {"type": "EMOJI", "content": "👍", "messageId": test_id},
    ]

    for i, attach in enumerate(reaction_attaches):
        payload = {
            "chatId": SASHA,
            "message": {
                "text": "",
                "attaches": [attach],
                "cid": int(time.time() * 1000) + i
            },
            "notify": False
        }
        r = req(ws, 20+i, 64, payload)
        if r:
            print(f"  try{i}: {json.dumps(attach, ensure_ascii=False)[:60]} → cmd={r.get('cmd')} pl={json.dumps(r.get('payload',{}), ensure_ascii=False)[:200]}")
        time.sleep(1)

    # Check if any reaction was added
    r = req(ws, 30, 71, {"chatId": SASHA, "messageIds": [test_id]})
    new_ri = r.get("payload", {}).get("messages", [{}])[0].get("reactionInfo", {})
    print(f"  AFTER: reactionInfo: {json.dumps(new_ri, ensure_ascii=False)[:400]}")
    if new_ri:
        print("  ✅ REACTION via MSG_SEND worked!")
    else:
        print("  ❌ No effect via MSG_SEND")

ws.close()

# ── PHASE 3: Try opcode 75 with reaction type from presets ──
print("\nPHASE 3: Opcode 75 with emoji IDs/animoji presets")
ws = connect()
init(ws, 50)

# Get reaction presets for animoji IDs
r = req(ws, 53, 26, {"type": "reaction", "marker": 0, "count": 20})
reaction_data = r.get("payload", {})
animojis = reaction_data.get("animojis", [])
print(f"  Animojis count: {len(animojis)}")
for a in animojis[:5]:
    print(f"    animoji: {json.dumps(a, ensure_ascii=False)[:200]}")

# Get emoji presets for emoji IDs
r = req(ws, 54, 26, {"type": "emoji", "marker": 0, "count": 20})
emoji_data = r.get("payload", {})
emojis = emoji_data.get("emojis", [])
print(f"  Emojis count: {len(emojis)}")
for e in emojis[:5]:
    print(f"    emoji: {json.dumps(e, ensure_ascii=False)[:200]}")

# If we have emoji or animoji with IDs, try using those IDs
if animojis:
    animoji_id = animojis[0].get("id") or animojis[0].get("entityId")
    print(f"\n  Trying with animoji id={animoji_id}")
    r = req(ws, 55, 75, {"chatId": SASHA, "messageId": test_id or 0, "reactionId": animoji_id})
    print(f"    75: cmd={r.get('cmd')} pl={json.dumps(r.get('payload',{}), ensure_ascii=False)[:200]}")
    time.sleep(1)

if emojis:
    emoji_id = emojis[0].get("id") or emojis[0].get("entityId")
    pack_id = emojis[0].get("packId")
    print(f"\n  Trying with emoji id={emoji_id} packId={pack_id}")
    r = req(ws, 56, 75, {"chatId": SASHA, "messageId": test_id or 0, "packId": pack_id, "id": emoji_id})
    print(f"    75: cmd={r.get('cmd')} pl={json.dumps(r.get('payload',{}), ensure_ascii=False)[:200]}")
    time.sleep(1)

ws.close()

# ── PHASE 4: Quick scan of opcodes 27-30 with reaction payloads ──
print("\nPHASE 4: Opcodes 27-31 (reaction candidates)")
for op in range(27, 32):
    ws = connect()
    init(ws, op*10)
    r = req(ws, op*10+3, op, {"chatId": SASHA, "messageId": test_id or 0, "emoji": "👍"})
    cmd = r.get("cmd") if r else "timeout"
    if cmd == 1:
        pl = r.get("payload", {})
        print(f"  [{op}] ACK: {json.dumps(pl, ensure_ascii=False)[:200]}")
    elif cmd == 3:
        err = r.get("payload", {}).get("message") or r.get("payload", {}).get("error") or str(r.get("payload"))[:200]
        print(f"  [{op}] ERR: {err}")
    ws.close()

print("\nDONE")
