#!/usr/bin/env python3
"""
Комплексное исследование недокументированных аспектов MAX API.

Запуск:
  python3 scripts/investigate.py

Скрипт открывает ОДНО постоянное WebSocket-соединение и
последовательно тестирует множество опкодов/функций.
"""
import json, os, ssl, sys, time, hashlib, re
from websocket import create_connection
import certifi

CONFIG_FILE = os.path.expanduser("~/claude-home/config/max_config.json")

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

config = load_config()
TOKEN = config["access_token"]
DID = config["device_id"]

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

# Тестовый чат Саши Шипиловой (разрешён для тестов)
TEST_CHAT = 309052361
MY_USER_ID = 3260455

class MaxConn:
    """Постоянное WebSocket-соединение."""
    def __init__(self):
        self.ws = None
        self.seq = 0
        self.pending = {}

    def connect(self):
        self.ws = create_connection(
            "wss://ws-api.oneme.ru/websocket",
            sslopt={"ca_certs": certifi.where()},
            timeout=15,
            header=[
                "Origin: https://web.max.ru",
                "User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:144.0)"
            ]
        )
        # INIT
        self._req(6, {
            "deviceId": DID,
            "userAgent": {
                "deviceType": "WEB", "locale": "ru", "deviceLocale": "ru",
                "osVersion": "Linux", "deviceName": "Firefox",
                "headerUserAgent": "Mozilla/5.0",
                "appVersion": "25.11.1",
                "screen": "1080x1920 1.0x",
                "timezone": "Asia/Yekaterinburg"
            }
        })
        # LOGIN
        self._req(19, {
            "token": TOKEN,
            "interactive": True,
            "chatsCount": 50,
            "chatsSync": 50,
            "contactsSync": 0,
            "presenceSync": 0,
            "draftsSync": 0
        })
        print("✓ Соединение установлено\n")

    def _req(self, opcode, payload=None):
        self.seq += 1
        msg = json.dumps({
            "ver": 11, "cmd": 0,
            "seq": self.seq,
            "opcode": opcode,
            "payload": payload or {}
        })
        self.ws.send(msg)
        return self.seq

    def _recv(self, timeout=10.0):
        """Получить следующий фрейм (любой cmd)."""
        self.ws.settimeout(timeout)
        try:
            raw = self.ws.recv()
            if raw:
                return json.loads(raw)
        except Exception:
            return None
        return None

    def call(self, opcode, payload=None, timeout=15.0):
        """Отправить запрос и дождаться ответа с тем же seq."""
        seq = self._req(opcode, payload)
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self._recv(timeout=5)
            if msg is None:
                continue
            # Push
            if msg.get("cmd") == 0:
                self._handle_push(msg)
                continue
            if msg.get("seq") == seq:
                if msg.get("cmd") == 1:
                    return ("ok", msg.get("payload", {}))
                elif msg.get("cmd") == 3:
                    return ("error", msg.get("payload", {}))
        return ("timeout", None)

    def call_raw(self, opcode, payload=None, timeout=15.0):
        """Как call, но возвращает весь фрейм."""
        seq = self._req(opcode, payload)
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self._recv(timeout=5)
            if msg is None:
                continue
            if msg.get("cmd") == 0:
                self._handle_push(msg)
                continue
            if msg.get("seq") == seq:
                return msg
        return None

    def _handle_push(self, msg):
        op = msg.get("opcode")
        pl = msg.get("payload", {})
        if op == 1:  # PING
            self._req(1, {"interactive": True})

    def close(self):
        if self.ws:
            self.ws.close()


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_result(name, status, detail="", data=None):
    icon = "✅" if status == "OK" else "⚠️" if status == "PARTIAL" else "❌" if status == "FAIL" else "ℹ️"
    print(f"  {icon} {name}: {detail}")
    if data:
        # Print compact JSON
        s = json.dumps(data, ensure_ascii=False, default=str)
        if len(s) > 2000:
            print(f"     (data: {len(s)} chars)")
        else:
            print(f"     {s}")

# ———————————————————————————————————————————————————————
def run_investigation():
    c = MaxConn()
    c.connect()

    # ─── 1. STRUCTURE: elements[] with links ──────────────
    section("1. ELEMENTS — отправка сообщения с ссылкой")
    # Отправляем сообщение с URL и проверяем elements[] в ответе
    result = c.call(64, {
        "chatId": TEST_CHAT,
        "message": {
            "text": "Тестовая ссылка https://example.com/test123",
            "cid": int(time.time() * 1000),
            "elements": [],
            "attaches": []
        },
        "notify": True
    })
    status, pl = result
    if status == "ok":
        msg_data = pl.get("message", pl)
        elements = msg_data.get("elements", "NOT_IN_RESPONSE")
        test_result("MSG_SEND с URL", "OK",
                    f"reply: elements={elements}")
        # Сохраняем id для удаления
        msg_id = msg_data.get("id")
        if msg_id:
            # Удалим тестовое сообщение
            c.call(66, {"chatId": TEST_CHAT, "messageIds": [msg_id], "forMe": False})
    else:
        test_result("MSG_SEND с URL", "FAIL", str(pl))

    # ─── 2. SEARCH_MESSAGES (73) ──────────────────────────
    section("2. SEARCH_MESSAGES (73)")

    # 2a. С chatId
    result = c.call(73, {"chatId": TEST_CHAT, "text": "тест", "count": 3})
    test_result("С chatId", "OK" if result[0] == "ok" else "FAIL",
                json.dumps(result[1], ensure_ascii=False)[:300] if result[0] == "ok" else str(result[1]),
                result[1] if result[0] == "ok" else None)

    # 2b. Без chatId (глобальный поиск)
    result = c.call(73, {"text": "MAX", "count": 3})
    test_result("Глобальный (без chatId)", "OK" if result[0] == "ok" else "FAIL",
                json.dumps(result[1], ensure_ascii=False)[:300] if result[0] == "ok" else str(result[1]),
                result[1] if result[0] == "ok" else None)

    # ─── 3. CHAT_SUBSCRIBE (84) ──────────────────────────
    section("3. CHAT_SUBSCRIBE (84)")
    # Попробуем разные форматы
    formats = [
        {"chatIds": [TEST_CHAT], "action": "subscribe"},
        {"chatIds": [TEST_CHAT]},
        {"chatId": TEST_CHAT},
    ]
    for i, fmt in enumerate(formats):
        result = c.call(84, fmt)
        test_result(f"Формат {i+1}: {fmt}", "OK" if result[0] == "ok" else "FAIL",
                    json.dumps(result[1], ensure_ascii=False)[:200])

    # ─── 4. CHAT_SHOW (86) ──────────────────────────────
    section("4. CHAT_SHOW (86) hide (show: false)")
    formats86 = [
        # Просто show=false
        {"chatId": TEST_CHAT, "show": False},
        # С дополнительными полями
        {"chatId": TEST_CHAT, "show": False, "notify": False},
        # show=true (показать обратно)
        {"chatId": TEST_CHAT, "show": True},
    ]
    for fmt in formats86:
        result = c.call(86, fmt)
        test_result(f"CHAT_SHOW {fmt}", "OK" if result[0] == "ok" else "FAIL",
                    json.dumps(result[1], ensure_ascii=False)[:200])

    # ─── 5. GET_USERINFO (177) ──────────────────────────
    section("5. GET_USERINFO (177)")
    # Разные форматы
    formats177 = [
        {"contactIds": [MY_USER_ID]},
        {"userIds": [MY_USER_ID], "time": int(time.time() * 1000)},
        {"userId": MY_USER_ID},
    ]
    for fmt in formats177:
        result = c.call(177, fmt)
        test_result(f"Формат: {fmt}", "OK" if result[0] == "ok" else "FAIL",
                    json.dumps(result[1], ensure_ascii=False)[:300])

    # ─── 6. MSG_FWD (68) — возможная пересылка ──────────
    section("6. MSG_FWD (68) — пересылка")
    formats68 = [
        {"chatId": TEST_CHAT, "messageIds": ["test"]},
        {"chatId": TEST_CHAT, "messageId": "test"},
        {"chatId": TEST_CHAT, "text": "test"},
    ]
    for fmt in formats68:
        result = c.call(68, fmt)
        test_result(f"Формат: {fmt}", "OK" if result[0] == "ok" else "FAIL",
                    json.dumps(result[1], ensure_ascii=False)[:200])

    # ─── 7. FORWARD_MESSAGE (70) ─────────────────────────
    section("7. FORWARD_MESSAGE (70)")
    # Сначала получим ID сообщения
    history = c.call(49, {"chatId": TEST_CHAT, "backward": 1, "forward": 0, "from": int(time.time() * 1000), "getMessages": True})
    sample_msg_id = None
    if history[0] == "ok":
        msgs = history[1].get("messages", [])
        if msgs:
            sample_msg_id = msgs[0].get("id")
            test_result("Получен sample message", "OK", f"id={sample_msg_id}")

    if sample_msg_id:
        formats70 = [
            {"chatId": TEST_CHAT, "messageId": sample_msg_id},
            {"chatId": TEST_CHAT, "messageIds": [sample_msg_id]},
            {"chatId": TEST_CHAT, "forwardFrom": TEST_CHAT, "messageIds": [sample_msg_id]},
            {"chatId": TEST_CHAT, "messageId": sample_msg_id, "text": "пересылаю"},
        ]
        for fmt in formats70:
            result = c.call(70, fmt)
            test_result(f"Формат: {fmt}", "OK" if result[0] == "ok" else "FAIL",
                        json.dumps(result[1], ensure_ascii=False)[:200])

    # ─── 8. GET_MEDIA (51) ──────────────────────────────
    section("8. GET_MEDIA (51)")
    # Проверяем разные типы медиа
    media_formats = [
        {"chatId": TEST_CHAT, "type": "AUDIO"},
        {"chatId": TEST_CHAT, "type": "FILE"},
        {"chatId": TEST_CHAT, "type": "SHARE"},
        {"chatId": TEST_CHAT},
    ]
    for fmt in media_formats:
        result = c.call(51, fmt)
        test_result(f"GET_MEDIA {fmt}", "OK" if result[0] == "ok" else "FAIL",
                    json.dumps(result[1], ensure_ascii=False)[:300])

    # ─── 9. CHAT_ACTIVITY (92) ──────────────────────────
    section("9. CHAT_ACTIVITY (92)")
    now = int(time.time() * 1000)
    formats92 = [
        {"chatId": TEST_CHAT, "startTime": now - 86400000, "endTime": now},  # за сутки
        {"chatId": TEST_CHAT, "startTime": now - 86400000, "endTime": now, "interactive": True},
    ]
    for fmt in formats92:
        result = c.call(92, fmt)
        test_result(f"CHAT_ACTIVITY", "OK" if result[0] == "ok" else "FAIL",
                    json.dumps(result[1], ensure_ascii=False)[:300])

    # ─── 10. GET_CHAT_INFO (61) для сравнения ────────────
    section("10. GET_CHAT_INFO (61) — сравнение с CHAT_ACTIVITY")
    result = c.call(61, {"chatId": TEST_CHAT})
    test_result("GET_CHAT_INFO", "OK" if result[0] == "ok" else "FAIL",
                json.dumps(result[1], ensure_ascii=False)[:300])

    # ─── 11. Полная история сообщений — ищем поля options, elements ──
    section("11. Детальный разбор структуры сообщений")
    # Получаем историю с max полями
    result = c.call(49, {
        "chatId": TEST_CHAT, "backward": 5, "forward": 0,
        "from": int(time.time() * 1000), "getMessages": True, "getChat": True
    })
    if result[0] == "ok":
        msgs = result[1].get("messages", [])
        test_result("История сообщений", "OK", f"{len(msgs)} сообщений")
        # Анализируем каждое сообщение на наличие редких полей
        for m in msgs:
            msg_id = m.get("id", "?")
            fields = set(m.keys())
            # Поля, которые нас интересуют
            interesting = ["elements", "options", "fwd", "forward", "watermark",
                          "replyTo", "reply", "updateTime", "status", "deleted",
                          "stats", "scheduleDate", "ttl"]
            found = {f: m.get(f) for f in interesting if f in m}
            if found:
                test_result(f"  msg {msg_id}", "ℹ️", f"поля: {json.dumps(found, ensure_ascii=False, default=str)[:500]}")

    # ─── 12. Проверка CHAT_OPERATION (77) тип действия ──
    section("12. CHAT_OPERATION (77) — типы операций")
    # Проверяем разные chatIds/форматы
    chat_types = [TEST_CHAT, -72842705805946]  # DIALOG + CHAT
    for cid in chat_types:
        result = c.call(61, {"chatId": cid})
        test_result(f"GET_CHAT_INFO [{cid}]", "OK" if result[0] == "ok" else "FAIL",
                    json.dumps(result[1], ensure_ascii=False)[:200])

    # ─── 13. CONTACT INFO через опкод 32 (raw) ──────────
    section("13. CONTACT INFO (32) — структура")
    result = c.call(32, {"contactIds": [MY_USER_ID, 6236697]})
    test_result("CONTACT INFO", "OK" if result[0] == "ok" else "FAIL",
                json.dumps(result[1], ensure_ascii=False)[:500])

    # ─── 14. Проверка системного чата (0) ────────────────
    section("14. Chat ID=0 — системный чат")
    result = c.call(49, {
        "chatId": 0, "backward": 3, "forward": 0,
        "from": int(time.time() * 1000), "getMessages": True
    })
    test_result("GET_HISTORY chatId=0", "OK" if result[0] == "ok" else "FAIL",
                json.dumps(result[1], ensure_ascii=False)[:300])

    result = c.call(61, {"chatId": 0})
    test_result("GET_CHAT_INFO chatId=0", "OK" if result[0] == "ok" else "FAIL",
                json.dumps(result[1], ensure_ascii=False)[:300])

    # ─── 15. MSG_REACT_SET — реакции ─────────────────────
    section("15. MSG_REACT_SET — реакции")
    # Попробуем разные форматы для реакции
    # Сначала получим последнее сообщение
    history = c.call(49, {"chatId": TEST_CHAT, "backward": 1, "forward": 0, "from": int(time.time() * 1000), "getMessages": True})
    last_id = None
    if history[0] == "ok":
        msgs = history[1].get("messages", [])
        if msgs:
            last_id = msgs[0].get("id")

    if last_id:
        # Пробуем разные форматы reactions
        reacts = [
            {"chatId": TEST_CHAT, "messageId": last_id, "reaction": "👍"},
            {"chatId": TEST_CHAT, "messageId": last_id, "reaction": "❤"},
            {"chatId": TEST_CHAT, "messageId": last_id, "emoji": "👍"},
            {"chatId": TEST_CHAT, "messageId": last_id, "reactionType": 1},
        ]
        for fmt in reacts:
            result = c.call(157, fmt)  # MSG_REACT_SET = 157
            test_result(f"REACT {fmt.get('reaction', fmt.get('emoji', fmt.get('reactionType', '?')))}",
                       "OK" if result[0] == "ok" else "FAIL",
                       json.dumps(result[1], ensure_ascii=False)[:200])

    # ─── 16. NOTIF_INCOMING_CALL (137) — фильтр по deviceId ──
    section("16. NOTIF_INCOMING_CALL (137) — проверка формата")
    # Этот опкод push-only, но пробуем отправить как запрос для проверки
    result = c.call(137, {"deviceId": DID})
    test_result("NOTIF_INCOMING_CALL как запрос", "OK" if result[0] == "ok" else "FAIL",
                json.dumps(result[1], ensure_ascii=False)[:200])

    c.close()
    print("\n✓ Исследование завершено")

if __name__ == "__main__":
    run_investigation()
