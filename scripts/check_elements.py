#!/usr/bin/env python3
"""Посмотреть elements[] из канальных сообщений — фикс seq."""
import json, os, ssl, time
from websocket import create_connection
import certifi

CONFIG_FILE = os.path.expanduser("~/claude-home/config/max_config.json")
with open(CONFIG_FILE) as f:
    config = json.load(f)

TOKEN, DID = config["access_token"], config["device_id"]

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
            except:
                continue
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

for label, chat_id in [("МАИ", -68335643047333), ("Володин", -68125341272812)]:
    print(f"\n=== {label} (chatId={chat_id}) ===")
    s.send(49, {"chatId": chat_id, "backward": 10, "forward": 0,
              "from": int(time.time()*1000), "getMessages": True})
    resp = s.recv()
    if not resp:
        print("  (нет ответа)")
        continue
    msgs = resp.get("payload", {}).get("messages", [])
    elems_found = 0
    for m in msgs:
        elems = m.get("elements", [])
        if elems:
            elems_found += 1
            mid = m.get("id","?")[:20]
            text_preview = m.get("text","")[:100]
            print(f"\n  msg {mid}")
            print(f"  text: {text_preview}")
            print(f"  elements: {json.dumps(elems, ensure_ascii=False, indent=4)}")
    if not elems_found:
        print("  (нет elements[])")

ws.close()
