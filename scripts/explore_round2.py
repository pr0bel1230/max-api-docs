#!/usr/bin/env /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""
Exploration Round 2:
- Scan opcodes 200-299
- Test opcode 92 (MSG_DELETE_RANGE)
- Attempt to find reaction opcodes
- Test MSG_EDIT (67) with full payload
- Test opcode 87 (FILE_UPLOAD)
- Re-test previously timing out opcodes 100-199
"""
import json, ssl, time, os, sys
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class Session:
    def __init__(self):
        self.ws, self.seq, self.user_id = None, 0, None

    def connect(self):
        self.ws = create_connection("wss://ws-api.oneme.ru/websocket",
            header=["Origin: https://web.max.ru", "User-Agent: Mozilla/5.0"],
            timeout=15, sslopt={"context": _ssl_ctx})
        self.seq += 1
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":6,"payload":{"userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},"deviceId":DID}}))
        self.seq += 1
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":19,"payload":{"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0}}))
        for _ in range(10):
            r = self._r(10)
            if r and r.get("cmd") == 1 and r.get("opcode") == 19:
                self.user_id = r.get("payload", {}).get("userId", 3260455)
                return True
            if r and r.get("cmd") == 3 and r.get("opcode") == 19:
                print(f"  {RED}LOGIN FAILED: {r.get('payload', {}).get('message', '')}{RESET}")
                return False
        return False

    def req(self, op, pl, t=20):
        self.seq += 1
        req_id = self.seq
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":req_id,"opcode":op,"payload":pl}))
        deadline = time.time() + t
        while time.time() < deadline:
            r = self._r(8)
            if r:
                if r.get("cmd") == 0:
                    continue
                if r.get("seq") == req_id:
                    return r
        return None

    def _r(self, t=5):
        if not self.ws:
            return None
        self.ws.settimeout(t)
        try:
            r = self.ws.recv()
            return json.loads(r) if r else None
        except:
            return None

    def close(self):
        if self.ws:
            try:
                self.ws.close()
            except:
                pass


def probe_op(opcode, payload, timeout=20):
    """One clean connection, one request."""
    s = Session()
    try:
        if not s.connect():
            return None
        return s.req(opcode, payload, t=timeout)
    except:
        return None
    finally:
        s.close()


def result(op, resp):
    if resp is None:
        return f"{YELLOW}TIMEOUT{RESET}"
    cmd = resp.get("cmd")
    if cmd == 1:
        pl = resp.get("payload", {})
        s = json.dumps(pl, ensure_ascii=False)[:400]
        if len(s) > 400:
            s = s[:397] + "..."
        return f"{GREEN}ACK{RESET} {s}"
    elif cmd == 3:
        err = resp.get("payload", {})
        msg = (err.get("message") or err.get("error") or str(err))[:200]
        return f"{RED}ERR{RESET} {msg}"
    return f"{YELLOW}cmd={cmd}{RESET} {str(resp)[:200]}"


def smart_req(s, op, pl, label):
    """Request through existing session."""
    r = s.req(op, pl)
    print(f"  {label:<30s} → {result(op, r)}")
    return r


# ────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────
print(f"{BOLD}{CYAN}🚀 MAX API - Exploration Round 2{RESET}\n")

# 0. Verify token
s = Session()
if not s.connect():
    print(f"  {RED}❌ Токен протух!{RESET}")
    sys.exit(1)
uid = s.user_id
print(f"  ✅ Токен жив! userId={uid}")
s.close()

# ────────────────────────────────────────────────────────────
# 1. SCAN 200-299
# ────────────────────────────────────────────────────────────
print(f"\n{BOLD}1️⃣  Сканирование опкодов 200-299{RESET}")
found  = []
errors = []
timeouts = []

for op in range(200, 300):
    r = probe_op(op, {"chatId": SASHA})
    if r and r.get("cmd") == 1:
        found.append(op)
        print(f"  ✅ [{op:3d}] {result(op, r)}")
    elif r and r.get("cmd") == 3:
        errors.append(op)
    else:
        timeouts.append(op)
    time.sleep(0.1)

print(f"\n  Итого: {GREEN}{len(found)} найдено{RESET}, {RED}{len(errors)} ошибок{RESET}, {YELLOW}{len(timeouts)} таймаутов{RESET}")

# 1b. Detail errors in 200-299
if errors:
    print(f"\n  {BOLD}Детализация ошибок 200-299:{RESET}")
    for op in errors[:15]:
        r = probe_op(op, {"chatId": SASHA})
        print(f"    [{op:3d}] {result(op, r)}")
        time.sleep(0.1)

# ────────────────────────────────────────────────────────────
# 2. OPCODE 92 — MSG_DELETE_RANGE
# ────────────────────────────────────────────────────────────
print(f"\n{BOLD}2️⃣  OPCODE 92 — MSG_DELETE_RANGE{RESET}")

for pl, label in [
    ({}, "empty"),
    ({"chatId": SASHA}, "only chatId"),
    ({"chatId": SASHA, "fromId": 0, "toId": 999999999999999999, "forMe": True}, "full range forMe"),
    ({"chatId": SASHA, "forMe": True}, "only forMe"),
]:
    r = probe_op(92, pl)
    print(f"  {label:<30s} → {result(92, r)}")

# ────────────────────────────────────────────────────────────
# 3. REACTION SEARCH
# ────────────────────────────────────────────────────────────
print(f"\n{BOLD}3️⃣  Поиск опкодов реакций{RESET}")

# Get a real message
print(f"  Получаем сообщение из истории...")
s = Session()
s.connect()
hist = s.req(49, {"chatId": SASHA, "backward": 5, "getMessages": True})
msg_id = None
reaction_msg_id = None
if hist and hist.get("cmd") == 1:
    msgs = hist.get("payload", {}).get("messages", [])
    if msgs:
        msg_id = msgs[0].get("id", "")
        print(f"  ✅ messageId={msg_id} (text: {msgs[0].get('text', '')[:80]})")
        for m in msgs:
            if m.get("sender") == uid:
                reaction_msg_id = m.get("id", "")
                print(f"  ✅ своё messageId={reaction_msg_id} (для реакций на своё)")
                break
    else:
        print(f"  {YELLOW}Нет сообщений в истории{RESET}")

# Try reaction payloads on promising opcodes
reaction_tests = [
    # opcode, payload
    (68, {"chatId": SASHA, "messageId": msg_id or 0, "reaction": {"type": "emoji", "content": "👍"}}),
    (68, {"chatId": SASHA, "messageId": msg_id or 0, "emoji": "👍"}),
    (75, {"chatId": SASHA, "messageId": msg_id or 0, "reaction": {"type": "emoji", "content": "👍"}}),
    (75, {"chatId": SASHA, "messageId": msg_id or 0, "reactionType": "LIKE"}),
    (75, {"chatId": SASHA, "messageId": msg_id or 0, "emoji": "❤️"}),
    (76, {"chatId": SASHA, "messageId": msg_id or 0, "reaction": "👍"}),
    (76, {"chatId": SASHA, "messageId": msg_id or 0, "reactionType": "like", "messageAuthor": uid}),
    (81, {"chatId": SASHA, "messageId": msg_id or 0, "emoji": "🔥"}),
    (82, {"chatId": SASHA, "messageId": msg_id or 0, "reaction": {"type": "emoji", "content": "👍"}}),
    (83, {"chatId": SASHA, "messageId": reaction_msg_id or 0, "messageAuthor": uid, "emojiType": "like"}),
    (84, {"chatId": SASHA, "messageId": reaction_msg_id or 0, "author": uid, "reactionId": "👍"}),
    (85, {"chatId": SASHA, "messageId": msg_id or 0}),
    (86, {"chatId": SASHA, "messageId": msg_id or 0}),
    (88, {"chatId": SASHA, "messageId": msg_id or 0, "reaction": "❤️"}),
    (89, {"chatId": SASHA, "messageId": msg_id or 0}),
    (90, {"chatId": SASHA, "messageId": msg_id or 0}),
    (91, {"chatId": SASHA, "messageId": msg_id or 0}),
    (93, {"chatId": SASHA, "messageId": msg_id or 0}),
    (94, {"chatId": SASHA, "messageId": msg_id or 0}),
    (99, {"chatId": SASHA, "messageId": msg_id or 0}),
]

for op, pl in reaction_tests:
    label = json.dumps(pl, ensure_ascii=False, sort_keys=True)[:60]
    r = probe_op(op, pl)
    print(f"  [{op:3d}] {label:<60s} → {result(op, r)}")

s.close()

# ────────────────────────────────────────────────────────────
# 4. OPCODE 67 — MSG_EDIT
# ────────────────────────────────────────────────────────────
print(f"\n{BOLD}4️⃣  OPCODE 67 — MSG_EDIT детально{RESET}")

# Get own message
s = Session()
s.connect()
edit_msg_id = None
if s.connect():
    hist = s.req(49, {"chatId": SASHA, "backward": 10, "getMessages": True})
    if hist and hist.get("cmd") == 1:
        msgs = hist.get("payload", {}).get("messages", [])
        for m in msgs:
            if m.get("sender") == uid:
                edit_msg_id = m.get("id")
                print(f"  ✅ Своё сообщение: id={edit_msg_id}, text=\"{m.get('text','')[:60]}\"")
                break
        if not edit_msg_id:
            print(f"  {YELLOW}Нет своих сообщений для редактирования{RESET}")

if edit_msg_id:
    edit_tests = [
        ({"chatId": SASHA, "messageId": edit_msg_id, "text": "Тест edit 1"}, "minimal text"),
        ({"chatId": SASHA, "messageId": edit_msg_id, "text": "Тест edit 2", "elements": []}, "text+elements"),
        ({"chatId": SASHA, "messageId": edit_msg_id, "text": "Тест edit 3", "elements": [], "attaches": []}, "text+elem+att"),
        ({"chatId": SASHA, "messageId": edit_msg_id, "text": "Тест edit 4", "cid": int(time.time()*1000)}, "text+cid"),
        ({"chatId": SASHA, "messageId": edit_msg_id, "text": "", "elements": []}, "empty+text+elem"),
    ]
    for pl, label in edit_tests:
        s = Session()
        s.connect()
        smart_req(s, 67, pl, label)
        s.close()

s.close()

# ────────────────────────────────────────────────────────────
# 5. OPCODE 87 — FILE_UPLOAD
# ────────────────────────────────────────────────────────────
print(f"\n{BOLD}5️⃣  OPCODE 87 — FILE_UPLOAD{RESET}")

for pl, label in [
    ({}, "empty"),
    ({"chatId": SASHA}, "only chatId"),
    ({"chatId": SASHA, "fileName": "test.txt", "fileSize": 100}, "with meta"),
]:
    r = probe_op(87, pl)
    print(f"  {label:<30s} → {result(87, r)}")

# ────────────────────────────────────────────────────────────
# 6. OPS 100-199 RE-TEST
# ────────────────────────────────────────────────────────────
print(f"\n{BOLD}6️⃣  Повторная проверка таймаутов 100-199{RESET}")
candidates = [100, 101, 102, 103, 110, 112, 113, 114, 115, 116, 118, 119, 120,
              121, 122, 123, 124, 125, 128, 129, 130, 131, 133, 135, 137, 138,
              139, 141, 143, 145, 146, 147, 148, 149, 150]

fresh_found = []
for op in candidates:
    r = probe_op(op, {"chatId": SASHA})
    if r and r.get("cmd") == 1:
        fresh_found.append(op)
        print(f"  {GREEN}✅ [{op:3d}] ACK! {result(op, r)}{RESET}")
    elif r and r.get("cmd") == 3:
        e = r.get("payload", {})
        msg = (e.get("message") or e.get("error") or str(e))[:100]
        print(f"  [{op:3d}] ERR: {msg}")

if not fresh_found:
    print(f"  {YELLOW}Все по-прежнему таймаут или ошибка{RESET}")

# ────────────────────────────────────────────────────────────
# DONE
# ────────────────────────────────────────────────────────────
print(f"\n{BOLD}{CYAN}🏁 Исследование завершено!{RESET}")
