#!/usr/bin/env /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""
Test opcode 75 as reaction endpoint.
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926

ws = create_connection("wss://ws-api.oneme.ru/websocket",
    header=["Origin: https://web.max.ru"], timeout=15, sslopt={"context": _ssl_ctx})

def req(seq, op, pl):
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":seq,"opcode":op,"payload":pl}))
    deadline = time.time() + 20
    while time.time() < deadline:
        r = json.loads(ws.recv())
        if r.get("cmd") == 0:
            continue
        if r.get("seq") == seq:
            return r
    return None

def init():
    req(1, 6, {"userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},"deviceId":DID})
    req(2, 19, {"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0})

init()
now_ms = int(time.time() * 1000)

# Get recent messages
r = req(3, 49, {"chatId": SASHA, "backward": 10, "getMessages": True, "from": now_ms})
msgs = r.get("payload", {}).get("messages", [])
msgs = [m for m in msgs if m.get("type") == "USER"]
if not msgs:
    print("No messages found")
    exit(1)

test_id = msgs[0].get("id")
print(f"Message: id={test_id} text=\"{msgs[0].get('text', '')[:60]}\"")

# BEFORE
r = req(4, 71, {"chatId": SASHA, "messageIds": [test_id]})
old_ri = r.get("payload", {}).get("messages", [{}])[0].get("reactionInfo", {})
print(f"BEFORE reactionInfo: {json.dumps(old_ri, ensure_ascii=False)[:200]}")

# Try emoji variant (simplest)
r = req(5, 75, {"chatId": SASHA, "messageId": test_id, "emoji": "❤️"})
print(f"75 emoji=❤️: cmd={r.get('cmd')} pl={json.dumps(r.get('payload',{}), ensure_ascii=False)[:200]}")

time.sleep(1)

# AFTER
r = req(6, 71, {"chatId": SASHA, "messageIds": [test_id]})
new_ri = r.get("payload", {}).get("messages", [{}])[0].get("reactionInfo", {})
print(f"AFTER  reactionInfo: {json.dumps(new_ri, ensure_ascii=False)[:400]}")

if old_ri != new_ri:
    print("✅ REACTION WORKED!")
else:
    print("❌ No change. Trying reactionType=LIKE...")
    r = req(7, 75, {"chatId": SASHA, "messageId": test_id, "reactionType": "LIKE"})
    print(f"75 reactionType=LIKE: cmd={r.get('cmd')}")
    time.sleep(1)
    r = req(8, 71, {"chatId": SASHA, "messageIds": [test_id]})
    new_ri2 = r.get("payload", {}).get("messages", [{}])[0].get("reactionInfo", {})
    print(f"AFTER2 reactionInfo: {json.dumps(new_ri2, ensure_ascii=False)[:400]}")
    if old_ri != new_ri2:
        print("✅ REACTION WORKED with reactionType!")
    else:
        print("❌ Still no change.")

# Try 75 with reaction object
print("\nTrying reaction object variant...")
r = req(9, 75, {"chatId": SASHA, "messageId": test_id, "reaction": {"type": "emoji", "content": "🔥"}})
print(f"75 reaction obj: cmd={r.get('cmd')}")
time.sleep(1)
r = req(10, 71, {"chatId": SASHA, "messageIds": [test_id]})
new_ri3 = r.get("payload", {}).get("messages", [{}])[0].get("reactionInfo", {})
print(f"AFTER3 reactionInfo: {json.dumps(new_ri3, ensure_ascii=False)[:400]}")
if old_ri != new_ri3:
    print("✅ REACTION WORKED with reaction object!")

ws.close()
print("\nDONE")
