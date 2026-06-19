#!/usr/bin/env python3
"""
Комплексное исследование MAX API — единое соединение.
"""
import json, os, ssl, sys, time
from websocket import create_connection
import certifi

CONFIG_FILE = os.path.expanduser("~/claude-home/config/max_config.json")
with open(CONFIG_FILE) as f:
    config = json.load(f)

TOKEN = config["access_token"]
DID = config["device_id"]
TEST_CHAT = 309052361
MY_USER_ID = 3260455

class Session:
    def __init__(self):
        self.ws = None
        self.seq = 0

    def connect(self):
        self.seq = 0
        self.ws = create_connection(
            "wss://ws-api.oneme.ru/websocket",
            sslopt={"ca_certs": certifi.where()},
            timeout=15,
            header=["Origin: https://web.max.ru"]
        )
        s = self._send(6, {"deviceId": DID, "userAgent": {
            "deviceType": "WEB", "locale": "ru", "deviceLocale": "ru",
            "osVersion": "Linux", "deviceName": "Firefox",
            "headerUserAgent": "Mozilla/5.0",
            "appVersion": "25.11.1", "screen": "1080x1920 1.0x",
            "timezone": "Asia/Yekaterinburg"
        }})
        self._wait(s)
        s = self._send(19, {"token": TOKEN, "interactive": True,
            "chatsCount": 10, "chatsSync": 10, "contactsSync": 0,
            "presenceSync": 0, "draftsSync": 0})
        self._wait(s)

    def _send(self, opcode, payload=None):
        self.seq += 1
        self.ws.send(json.dumps({
            "ver": 11, "cmd": 0, "seq": self.seq,
            "opcode": opcode, "payload": payload or {}
        }))
        return self.seq

    def _wait(self, target_seq, timeout=12):
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.ws.settimeout(3)
            try:
                raw = self.ws.recv()
            except:
                continue
            if not raw:
                continue
            msg = json.loads(raw)
            if msg.get("cmd") == 0:
                if msg.get("opcode") == 1:
                    self._send(1, {"interactive": True})
                continue
            if msg.get("seq") == target_seq:
                return msg
        return None

    def call(self, opcode, payload=None, timeout=12):
        seq = self._send(opcode, payload)
        resp = self._wait(seq, timeout)
        if resp is None:
            return ("timeout", None)
        cmd = resp.get("cmd")
        pl = resp.get("payload", {})
        if cmd == 1:
            return ("ok", pl)
        elif cmd == 3:
            return ("error", pl)
        return (f"cmd={cmd}", pl)

    def safe_call(self, opcode, payload=None, timeout=12):
        """Вызов с автоматическим переподключением при падении соединения."""
        try:
            return self.call(opcode, payload, timeout)
        except Exception:
            try:
                self.ws.close()
            except:
                pass
            print("     ⚡ соединение потеряно, переподключаемся...")
            self.connect()
            return self.call(opcode, payload, timeout)

    def close(self):
        if self.ws:
            try:
                self.ws.close()
            except:
                pass


def sf(icon, name, status, detail=""):
    d = json.dumps(detail, ensure_ascii=False, default=str)[:400] if isinstance(detail, (dict, list)) else str(detail)[:400]
    print(f"  {icon} {name}: {status}")
    if d and status != "OK":
        print(f"     {d}")

# ============================================================
print("=" * 60)
print("  MAX API — массовое исследование (единое соединение)")
print("=" * 60)

s = Session()
s.connect()
print("✓ Подключено")

# ─── 1. MSG_SEND с URL + elements[] ──
print("\n── 1. ELEMENTS (MSG_SEND с URL) ──")
st, pl = s.safe_call(64, {
    "chatId": TEST_CHAT,
    "message": {"text": "Тест https://example.com/page", "cid": int(time.time() * 1000), "elements": [], "attaches": []},
    "notify": True
})
if st == "ok":
    msg = pl.get("message", pl)
    elem = msg.get("elements", "—")
    sf("✅", "elements в ответе", "OK", f"elements={json.dumps(elem, ensure_ascii=False)[:200]}")
    mid = msg.get("id")
    if mid:
        s.safe_call(66, {"chatId": TEST_CHAT, "messageIds": [mid], "forMe": False})
else:
    sf("❌", "MSG_SEND", st, pl)

# ─── 2. SEARCH_MESSAGES (73) ──
print("\n── 2. SEARCH_MESSAGES (73) ──")
for label, payl in [
    ("С chatId, query=тест", {"chatId": TEST_CHAT, "query": "тест", "count": 3}),
    ("Глобальный query=MAX", {"query": "MAX", "count": 3}),
]:
    st, pl = s.safe_call(73, payl)
    n = len(pl.get("messages", pl.get("items", []))) if st == "ok" else 0
    sf("✅" if st == "ok" else "❌", label, "OK" if st == "ok" else st,
       f"{n} результатов" if st == "ok" else pl)

# ─── 3. CHAT_SUBSCRIBE (84) ──
print("\n── 3. CHAT_SUBSCRIBE (84) ──")
for label, payl in [
    ("chatIds[]", {"chatIds": [TEST_CHAT], "action": "subscribe"}),
    ("chatIds[] без action", {"chatIds": [TEST_CHAT]}),
    ("chatId один", {"chatId": TEST_CHAT}),
]:
    st, pl = s.safe_call(84, payl)
    sf("✅" if st == "ok" else "❌", label, st, pl)

# ─── 4. CHAT_SHOW (86) ──
print("\n── 4. CHAT_SHOW (86) ──")
st1, pl1 = s.safe_call(86, {"chatId": TEST_CHAT, "show": False})
sf("✅" if st1 == "ok" else "❌", "show=false", st1, pl1)

st2, pl2 = s.safe_call(86, {"chatId": TEST_CHAT, "show": False, "notify": False})
sf("✅" if st2 == "ok" else "❌", "show=false+notify", st2, pl2)

st3, pl3 = s.safe_call(86, {"chatId": TEST_CHAT, "show": True})
sf("✅" if st3 == "ok" else "❌", "show=true (вернуть)", st3, pl3)

# ─── 5. GET_USERINFO (177) ──
print("\n── 5. GET_USERINFO (177) ──")
for label, payl in [
    ("contactIds[]", {"contactIds": [MY_USER_ID]}),
    ("userIds[]+time", {"userIds": [MY_USER_ID], "time": int(time.time() * 1000)}),
    ("userId один", {"userId": MY_USER_ID}),
]:
    st, pl = s.safe_call(177, payl)
    sf("✅" if st == "ok" else "❌", label, st, pl)

# ─── 6. MSG_FWD (68) ──
print("\n── 6. MSG_FWD (68) ──")
for label, payl in [
    ("messageIds[]", {"chatId": TEST_CHAT, "messageIds": ["test_id"]}),
    ("messageId", {"chatId": TEST_CHAT, "messageId": "test_id"}),
    ("только chatId", {"chatId": TEST_CHAT}),
]:
    st, pl = s.safe_call(68, payl)
    sf("✅" if st == "ok" else "❌", label, st, pl)

# ─── 7. FORWARD_MESSAGE (70) ──
print("\n── 7. FORWARD_MESSAGE (70) ──")
st, pl = s.safe_call(49, {"chatId": TEST_CHAT, "backward": 1, "forward": 0,
                          "from": int(time.time() * 1000), "getMessages": True})
sample_id = None
if st == "ok":
    msgs = pl.get("messages", [])
    if msgs:
        sample_id = msgs[0].get("id")
        sf("✅", "sample msg id", "OK", sample_id)

if sample_id:
    for label, payl in [
        ("messageId", {"chatId": TEST_CHAT, "messageId": sample_id}),
        ("messageIds[]", {"chatId": TEST_CHAT, "messageIds": [sample_id]}),
        ("forwardFrom", {"chatId": TEST_CHAT, "forwardFrom": TEST_CHAT, "messageIds": [sample_id]}),
        ("с текстом", {"chatId": TEST_CHAT, "messageId": sample_id, "text": "пересылка"}),
    ]:
        st, pl = s.safe_call(70, payl)
        sf("✅" if st == "ok" else "❌", label, st, pl)
else:
    sf("⚠️", "Нет сообщения для теста", "—")

# ─── 8. GET_MEDIA (51) ──
print("\n── 8. GET_MEDIA (51) ──")
for label, payl in [
    ("AUDIO", {"chatId": TEST_CHAT, "type": "AUDIO", "count": 3}),
    ("FILE", {"chatId": TEST_CHAT, "type": "FILE", "count": 3}),
    ("SHARE", {"chatId": TEST_CHAT, "type": "SHARE", "count": 3}),
    ("IMAGE", {"chatId": TEST_CHAT, "type": "IMAGE", "count": 3}),
    ("VIDEO", {"chatId": TEST_CHAT, "type": "VIDEO", "count": 3}),
    ("Без type", {"chatId": TEST_CHAT, "count": 3}),
]:
    st, pl = s.safe_call(51, payl)
    if st == "ok":
        items = pl.get("messages", pl.get("items", pl.get("media", [])))
        n = len(items) if isinstance(items, list) else "?"
        sf("✅", label, "OK", f"{n} элементов, type={pl.get('type','?')}")
    else:
        sf("❌", label, st, pl)

# ─── 9. CHAT_ACTIVITY (92) ──
print("\n── 9. CHAT_ACTIVITY (92) ──")
now = int(time.time() * 1000)
for label, payl in [
    ("За сутки", {"chatId": TEST_CHAT, "startTime": now - 86400000, "endTime": now}),
    ("interactive=True", {"chatId": TEST_CHAT, "startTime": now - 86400000, "endTime": now, "interactive": True}),
]:
    st, pl = s.safe_call(92, payl)
    sf("✅" if st == "ok" else "❌", label, st, pl)

# ─── 10. GET_CHAT_INFO (61) ──
print("\n── 10. GET_CHAT_INFO (61) ──")
st, pl = s.safe_call(61, {"chatId": TEST_CHAT})
if st == "ok":
    sf("✅", "GET_CHAT_INFO", "OK", f"поля: {list(pl.keys())}")
    for k in ["options", "settings"]:
        if k in pl:
            sf("ℹ️", f"  .{k}", "есть", json.dumps(pl[k], ensure_ascii=False)[:300])

# ─── 11. Детальные сообщения ──
print("\n── 11. Детальная структура сообщений ──")
# Основной чат
st, pl = s.safe_call(49, {"chatId": TEST_CHAT, "backward": 10, "forward": 0,
                          "from": int(time.time() * 1000), "getMessages": True, "getChat": True})
if st == "ok":
    msgs = pl.get("messages", [])
    sf("✅", f"История DIALOG", "OK", f"{len(msgs)} сообщений")
    for m in msgs:
        interesting = ["elements", "options", "fwd", "forward", "watermark",
                      "replyTo", "reply", "updateTime", "status", "deleted",
                      "stats", "scheduleDate", "ttl", "version"]
        found = {f: m[f] for f in interesting if f in m}
        if found:
            sf("ℹ️", f"  msg {str(m.get('id','?'))[:16]}...", "есть",
               json.dumps(found, ensure_ascii=False)[:400])

# Канальные сообщения
for cc in [-68335643047333, -68125341272812]:
    st, pl = s.safe_call(49, {"chatId": cc, "backward": 5, "forward": 0,
                              "from": int(time.time() * 1000), "getMessages": True})
    if st == "ok":
        msgs = pl.get("messages", [])
        for m in msgs:
            if "elements" in m:
                sf("✅", f"  Канал {cc}: elements найден", "OK",
                   json.dumps(m["elements"], ensure_ascii=False)[:300])

# ─── 12. Системный чат ──
print("\n── 12. Chat ID=0 ──")
st, pl = s.safe_call(61, {"chatId": 0})
if st == "ok":
    sf("✅", "GET_CHAT_INFO(0)", "OK",
       f"type={pl.get('type')} id={pl.get('id')} title={pl.get('title','?')}")
else:
    sf("❌", "GET_CHAT_INFO(0)", st, pl)

st, pl = s.safe_call(49, {"chatId": 0, "backward": 3, "forward": 0,
                          "from": int(time.time() * 1000), "getMessages": True})
if st == "ok":
    msgs = pl.get("messages", [])
    sf("✅", "GET_HISTORY(0)", "OK" if not msgs else f"{len(msgs)} сообщений",
       json.dumps(msgs[:2], ensure_ascii=False)[:300] if msgs else "пусто")
else:
    sf("❌", "GET_HISTORY(0)", st, pl)

# ─── 13. MSG_REACT_SET (157) ──
print("\n── 13. MSG_REACT_SET (157) ──")
st, pl = s.safe_call(49, {"chatId": TEST_CHAT, "backward": 1, "forward": 0,
                          "from": int(time.time() * 1000), "getMessages": True})
last_id = pl.get("messages", [{}])[0].get("id") if st == "ok" and pl.get("messages") else None
if last_id:
    for label, payl in [
        ("reaction=👍", {"chatId": TEST_CHAT, "messageId": last_id, "reaction": "👍"}),
        ("reactionType=1", {"chatId": TEST_CHAT, "messageId": last_id, "reactionType": 1}),
        ("emoji=👍", {"chatId": TEST_CHAT, "messageId": last_id, "emoji": "👍"}),
        ("messageIds[]", {"chatId": TEST_CHAT, "messageIds": [last_id], "reaction": "🔥"}),
    ]:
        st2, pl2 = s.safe_call(157, payl)
        sf("✅" if st2 == "ok" else "❌", label, st2, pl2)

# ─── 14. VOID / CHAT_ACTION ──
print("\n── 14. VOID/CHAT_ACTION ──")
for op in [100, 103]:
    st, pl = s.safe_call(op, {})
    sf("✅" if st == "ok" else "❌", f"VOID({op})", st, pl)

for label, payl in [
    ("CHAT_ACTION baseline", {"chatId": TEST_CHAT}),
    ("CHAT_ACTION typing", {"chatId": TEST_CHAT, "type": "typing"}),
]:
    st, pl = s.safe_call(72, payl)
    sf("✅" if st == "ok" else "❌", label, st, pl)

# ─── 15. GET_STATS (74) ──
print("\n── 15. GET_STATS (74) ──")
st, pl = s.safe_call(74, {"messageIds": ["test"]})
sf("✅" if st == "ok" else "❌", "GET_STATS", st, pl)

# ─── 16. CHAT vs GROUP ──
print("\n── 16. Типы чатов ──")
st, pl = s.safe_call(61, {"chatId": -72842705805946})
if st == "ok":
    sf("✅", "CHAT (Орлёнок)", "OK",
       f"type={pl.get('type')} title={pl.get('title','?')}")

# ─── 17. NOTIF_INCOMING_CALL (137) ──
print("\n── 17. NOTIF_INCOMING_CALL (137) ──")
st, pl = s.safe_call(137, {"deviceId": DID})
sf("✅" if st == "ok" else "❌", "137 как запрос", st, pl)

# ─── 18. Push-опкоды как запросы ──
print("\n── 18. Push-опкоды как запросы ──")
for op in [128, 129, 130, 132, 140, 142, 156]:
    st, pl = s.safe_call(op, {"chatId": TEST_CHAT})
    sf(("✅" if st == "ok" else "❌") or "❌", f"{op}", st, pl)

# ─── 19. SERVER_TIME ──
print("\n── 19. SERVER_TIME (200) ──")
st, pl = s.safe_call(200, {})
sf("✅" if st == "ok" else "❌", "SERVER_TIME", st, pl)

# Закрываем
s.close()
print("\n✓ Исследование завершено. Всего вызовов:", s.seq)
