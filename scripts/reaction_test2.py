#!/usr/bin/env /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""
Reaction test v2 — try message with text, various payloads.
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
        if r.get("cmd") == 0: continue
        if r.get("seq") == seq: return r
    return None

def init():
    req(1, 6, {"userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},"deviceId":DID})
    return req(2, 19, {"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0})

init()
now_ms = int(time.time() * 1000)

# Get messages with text
r = req(3, 49, {"chatId": SASHA, "backward": 50, "getMessages": True, "from": now_ms})
msgs = r.get("payload", {}).get("messages", [])
text_msgs = [m for m in msgs if m.get("text", "").strip() and m.get("type") == "USER"]
print(f"Text messages: {len(text_msgs)}/{len(msgs)}")

if text_msgs:
    test_id = text_msgs[0].get("id")
    txt = text_msgs[0].get("text", "")[:60]
    sender = text_msgs[0].get("sender")
    print(f"Testing: msgId={test_id} snd={sender} text=\"{txt}\"")

    # BEFORE
    r = req(4, 71, {"chatId": SASHA, "messageIds": [test_id]})
    old_ri = r.get("payload", {}).get("messages", [{}])[0].get("reactionInfo", {})
    print(f"BEFORE: {json.dumps(old_ri, ensure_ascii=False)[:200]}")

    # Try various payloads
    tests = [
        (5, 75, {"chatId": SASHA, "messageId": test_id, "emoji": "👍"}),
        (6, 75, {"chatId": SASHA, "messageId": test_id, "reaction": "like"}),
        (7, 75, {"chatId": SASHA, "messageId": test_id, "reactionId": 1}),
        (8, 75, {"chatId": SASHA, "messageId": test_id, "reactionType": "like", "reaction": "👍"}),
        (9, 75, {"chatId": SASHA, "messageId": test_id, "reactions": [{"type": "emoji", "content": "❤️"}]}),
        (10, 75, {"chatId": SASHA, "messageId": test_id, "messageAuthor": sender, "emoji": "😊"}),
        (11, 130, {"chatId": SASHA, "messageId": test_id, "emoji": "👍"}),  # just in case
        (12, 131, {"chatId": SASHA, "messageId": test_id, "emoji": "👍"}),  # just in case
    ]

    for seq, op, pl in tests:
        print(f"\n  [{op}] {json.dumps(pl, ensure_ascii=False)[:80]}")
        r = req(seq, op, pl)
        cmd = r.get("cmd")
        if cmd == 1:
            print(f"    ACK: {json.dumps(r.get('payload',{}), ensure_ascii=False)[:200]}")
        elif cmd == 3:
            err = r.get("payload", {}).get("message") or r.get("payload", {}).get("error") or str(r.get("payload"))[:200]
            print(f"    ERR: {err}")

    time.sleep(2)

    # AFTER — check all reactions
    r = req(20, 71, {"chatId": SASHA, "messageIds": [test_id]})
    new_ri = r.get("payload", {}).get("messages", [{}])[0].get("reactionInfo", {})
    print(f"\nAFTER: {json.dumps(new_ri, ensure_ascii=False)[:400]}")
    if old_ri != new_ri:
        print("✅ REACTION CHANGED!")
    else:
        print("❌ No change detected")

    # Try a different approach — maybe reaction needs specific reactionId numeric
    print("\n--- Trying numeric reactionIds ---")
    for reaction_id in range(1, 10):
        r = req(30+reaction_id, 75, {"chatId": SASHA, "messageId": test_id, "reactionId": reaction_id, "reactionType": "like"})
        if r.get("cmd") == 1:
            print(f"  reactionId={reaction_id}: ACK")
        elif r.get("cmd") == 3:
            e = r.get("payload", {}).get("message") or str(r.get("payload"))[:100]
            if "reaction" not in e.lower():  # only show non-reaction errors
                print(f"  reactionId={reaction_id}: {e}")

else:
    print("No text messages found")

ws.close()
print("\nDONE")
