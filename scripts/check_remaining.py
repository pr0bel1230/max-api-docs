#!/usr/bin/env python3
"""Добиваем оставшиеся вопросы."""
import json, os, ssl, time
from websocket import create_connection
import certifi

CONFIG_FILE = os.path.expanduser("~/claude-home/config/max_config.json")
with open(CONFIG_FILE) as f:
    config = json.load(f)
TOKEN, DID = config["access_token"], config["device_id"]
TEST_CHAT = 309052361
MY_USER_ID = 3260455

ws = create_connection("wss://ws-api.oneme.ru/websocket", sslopt={"ca_certs": certifi.where()}, timeout=15,
                       header=["Origin: https://web.max.ru"])

class S:
    def __init__(self):
        self.seq = 0
    def send(self, op, payload=None):
        self.seq += 1
        ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":op,"payload":payload or {}}))
        return self.seq
    def recv(self, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            ws.settimeout(3)
            try:
                raw = ws.recv()
            except: continue
            if not raw: continue
            msg = json.loads(raw)
            if msg.get("cmd") == 0 and msg.get("opcode") == 1:
                ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq+5000,"opcode":1,"payload":{"interactive":True}}))
                continue
            if msg.get("seq") == self.seq: return msg
        return None

s = S()
s.send(6, {"deviceId": DID, "userAgent": {"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"}})
s.recv()
s.send(19, {"token":TOKEN,"interactive":True,"chatsCount":10,"chatsSync":10,"contactsSync":0,"presenceSync":0,"draftsSync":0})
s.recv()

# 1. GET_MEDIA (51) — полный ответ
print("=== GET_MEDIA (51) детально ===")
for mtype in ["AUDIO", "FILE", "SHARE", "IMAGE", "VIDEO"]:
    s.send(51, {"chatId": TEST_CHAT, "type": mtype, "count": 3})
    resp = s.recv()
    if not resp: continue
    pl = resp.get("payload", {})
    # Покажем структуру ответа
    keys = list(pl.keys())
    items = pl.get("items", pl.get("messages", pl.get("media", [])))
    if isinstance(items, list) and items:
        print(f"\n  {mtype}: keys={keys}, items={len(items)}")
        print(f"    first: {json.dumps(items[0], ensure_ascii=False, default=str)[:400]}")
    else:
        print(f"\n  {mtype}: keys={keys}, items empty")

# 2. CHAT_SUBSCRIBE (84) — что такое conversationId?
# Проверим в логе LOGIN — возможно, это поле есть в чате
print("\n=== Поиск conversationId ===")
s.send(61, {"chatId": TEST_CHAT})
resp = s.recv()
if resp:
    pl = resp.get("payload", {})
    for k in ["conversationId", "conversation", "cid"]:
        v = pl.get(k)
        if v:
            print(f"  GET_CHAT_INFO.{k} = {v}")
    # Также проверим participants
    print(f"  participants: {pl.get('participants')}")

# 3. options и структура сообщений
print("\n=== options в сообщениях ===")
s.send(49, {"chatId": TEST_CHAT, "backward": 3, "forward": 0,
            "from": int(time.time()*1000), "getMessages": True, "getChat": True})
resp = s.recv()
if resp:
    pl = resp.get("payload", {})
    msgs = pl.get("messages", [])
    for m in msgs:
        mid = m.get("id","?")[:20]
        mkeys = list(m.keys())
        # Показываем ВСЕ ключи сообщения
        print(f"  msg {mid}: keys = {mkeys}")
        for k in ["options", "fwd", "forward", "watermark", "replyTo", "reply",
                  "updateTime", "status", "deleted", "stats", "elements"]:
            if k in m:
                val = m[k]
                print(f"    {k}: {json.dumps(val, ensure_ascii=False, default=str)[:300]}")

# 4. Статус CHAT vs GROUP
print("\n=== CHAT vs GROUP ===")
# из GET_CHATS уже знаем типы = DIALOG, CHAT, CHANNEL
# Но проверим через GET_CHAT_INFO для CHAT (Орлёнок)
s.send(61, {"chatId": -72842705805946})
resp = s.recv()
if resp:
    pl = resp.get("payload", {})
    print(f"  CHAT (Орлёнок): type={pl.get('type')}, title={pl.get('title','?')}")
    print(f"  keys: {list(pl.keys())}")

# 5. GET_STATS (74) — на реальных сообщениях из канала
print("\n=== GET_STATS (74) с channel message ===")
s.send(49, {"chatId": -68335643047333, "backward": 1, "forward": 0,
            "from": int(time.time()*1000), "getMessages": True})
resp = s.recv()
if resp:
    msgs = resp.get("payload", {}).get("messages", [])
    if msgs:
        mid = msgs[0].get("id")
        print(f"  channel msg id = {mid}")
        s.send(74, {"chatId": -68335643047333, "messageIds": [mid]})
        resp2 = s.recv()
        if resp2:
            print(f"  GET_STATS: {json.dumps(resp2.get('payload',{}), ensure_ascii=False)[:400]}")

# 6. MSG_REACT_SET (157) — рабочий формат
print("\n=== MSG_REACT_SET (157) ===")
s.send(49, {"chatId": TEST_CHAT, "backward": 1, "forward": 0,
            "from": int(time.time()*1000), "getMessages": True})
resp = s.recv()
if resp:
    msgs = resp.get("payload", {}).get("messages", [])
    if msgs:
        last_id = msgs[0].get("id")
        print(f"  last msg id = {last_id}")
        # Все возможные форматы
        for fmt, act in [
            ({"chatId": TEST_CHAT, "messageId": last_id, "reaction": "👍"}, "reaction=👍"),
            ({"chatId": TEST_CHAT, "messageId": last_id, "reactionType": 1}, "reactionType=1"),
            ({"chatId": TEST_CHAT, "messageId": last_id, "emoji": "👍"}, "emoji=👍"),
        ]:
            s.send(157, fmt)
            resp2 = s.recv()
            if resp2:
                cmd = resp2.get("cmd")
                print(f"  {act}: cmd={cmd}", end="")
                if cmd == 3:
                    print(f" error={json.dumps(resp2.get('payload'), ensure_ascii=False)[:200]}")
                else:
                    print(f" payload={json.dumps(resp2.get('payload'), ensure_ascii=False)[:200]}")

# 7. WATERMARK — что возвращает MSG_SEND
print("\n=== WATERMARK в MSG_SEND ===")
s.send(64, {"chatId": TEST_CHAT,
    "message": {"text": "check watermark", "cid": int(time.time()*1000), "elements": [], "attaches": []},
    "notify": True})
resp = s.recv()
if resp:
    pl = resp.get("payload", {})
    print(f"  MSG_SEND response keys: {list(pl.keys())}")
    msg = pl.get("message", {})
    print(f"  message keys: {list(msg.keys())}")
    if "watermark" in msg:
        print(f"  watermark: {msg['watermark']}")

# 8. Канал: есть ли fwd/forward/options
print("\n=== Канал: структура сообщения ===")
s.send(49, {"chatId": -68335643047333, "backward": 3, "forward": 0,
            "from": int(time.time()*1000), "getMessages": True})
resp = s.recv()
if resp:
    msgs = resp.get("payload", {}).get("messages", [])
    for m in msgs:
        mkeys = list(m.keys())
        print(f"  msg {m.get('id','?')[:16]}: keys = {mkeys}")
        # Покажем все кроме text
        for k in mkeys:
            if k not in ("text", "id", "chatId", "sender", "time", "type", "attaches", "cid", "reactionInfo"):
                print(f"    {k}: {json.dumps(m[k], ensure_ascii=False, default=str)[:300]}")

ws.close()
print("\n✓ Готово")
