#!/usr/bin/env python3
"""
Пример работы с MAX Messenger через WebSocket.

Команды:
  INIT (6)      — инициализация сессии
  LOGIN (19)    — авторизация по токену
  GET_CHATS (53) — список чатов
  MSG_SEND (64) — отправка сообщения
  GET_HISTORY (49) — история сообщений

Запуск:
  export ACCESS_TOKEN="токен из web.max.ru"
  export DEVICE_ID="device_id из INIT запроса"
  python3 example.py
"""
import json, os, ssl, sys, time
from websocket import create_connection
import certifi

TOKEN = os.environ.get("ACCESS_TOKEN") or sys.exit("Укажи ACCESS_TOKEN")
DID = os.environ.get("DEVICE_ID") or sys.exit("Укажи DEVICE_ID")

ssl_ctx = ssl.create_default_context(cafile=certifi.where())

def req(op, payload=None):
    """Формирует запрос в формате WebSocket MAX."""
    return json.dumps({
        "ver": 11, "cmd": 0,
        "seq": int(time.time() * 1000) & 0xFFFF,
        "opcode": op,
        "payload": payload or {}
    })

def ws_connect():
    ws = create_connection(
        "wss://ws-api.oneme.ru/websocket",
        sslopt={"ca_certs": certifi.where()},
        timeout=15
    )
    # INIT (opcode 6)
    ws.send(req(6, {
        "deviceId": DID,
        "userAgent": {
            "deviceType": "WEB",
            "locale": "ru",
            "deviceLocale": "ru",
            "osVersion": "Linux",
            "deviceName": "Firefox",
            "headerUserAgent": "Mozilla/5.0",
            "appVersion": "25.11.1",
            "screen": "1080x1920 1.0x",
            "timezone": "Asia/Yekaterinburg"
        }
    }))
    init = json.loads(ws.recv())
    print(f"INIT: cmd={init.get('cmd')}")
    # LOGIN (opcode 19)
    ws.send(req(19, {
        "token": TOKEN,
        "interactive": True,
        "chatsCount": 10,
        "chatsSync": 10,
        "contactsSync": 0,
        "presenceSync": 0,
        "draftsSync": 0
    }))
    login = json.loads(ws.recv())
    print(f"LOGIN: cmd={login.get('cmd')}")
    return ws

def get_chats(ws, count=5):
    """Список чатов (opcode 53)."""
    ws.send(req(53, {"count": count, "marker": int(time.time() * 1000)}))
    resp = json.loads(ws.recv())
    return resp.get("payload", {}).get("chats", [])

def send_message(ws, chat_id, text):
    """Отправить сообщение (opcode 64)."""
    payload = {
        "chatId": chat_id,
        "message": {
            "text": text,
            "cid": int(time.time() * 1000),
            "elements": [],
            "attaches": []
        },
        "notify": True
    }
    ws.send(req(64, payload))
    resp = json.loads(ws.recv())
    return resp.get("payload", {}).get("message", {})

def get_history(ws, chat_id, count=5):
    """История сообщений (opcode 49)."""
    payload = {
        "chatId": chat_id,
        "backward": count,
        "forward": 0,
        "from": int(time.time() * 1000),
        "getMessages": True
    }
    ws.send(req(49, payload))
    resp = json.loads(ws.recv())
    return resp.get("payload", {}).get("messages", [])

def main():
    ws = ws_connect()
    print("Подключено к MAX\n")

    # GET_CHATS
    chats = get_chats(ws)
    print(f"=== ЧАТЫ ({len(chats)}) ===\n")
    cid = None
    for c in chats[:5]:
        name = c.get("title", "(без названия)")
        print(f"  [{c['id']}] {name}")
        if not cid:
            cid = c["id"]
    if cid:
        print()
        # GET_HISTORY
        msgs = get_history(ws, cid, 3)
        print(f"=== ИСТОРИЯ чата [{cid}] (3 сообщ.) ===\n")
        for m in msgs:
            author_id = m.get("sender", "?")
            text = m.get("text", "")[:80]
            print(f"  sender={author_id}: {text}\n" if text else "  (вложение)\n")

        # MSG_SEND
        msg = send_message(ws, cid, "Привет! Это тест из example.py")
        mid = msg.get("id", "?")
        print(f"  Отправлено, id={mid}\n")
    ws.close()

if __name__ == "__main__":
    main()
