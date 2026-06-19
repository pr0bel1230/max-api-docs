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
        "ver": 11, "cmd": 2,
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
    ws.send(req(6, {"deviceId": DID, "ua": "max-api-example"}))
    init = json.loads(ws.recv())
    # LOGIN (opcode 19)
    ws.send(req(19, {"token": TOKEN}))
    login = json.loads(ws.recv())
    return ws

def get_chats(ws, count=5):
    """Список чатов (opcode 53)."""
    ws.send(req(53, {"count": count}))
    return json.loads(ws.recv())

def send_message(ws, chat_id, text):
    """Отправить сообщение (opcode 64)."""
    payload = {"chatId": chat_id, "text": text,
               "tempId": f"tmp_{int(time.time()*1000)}"}
    ws.send(req(64, payload))
    return json.loads(ws.recv())

def get_history(ws, chat_id, count=5):
    """История сообщений (opcode 49)."""
    ws.send(req(49, {"chatId": chat_id, "count": count}))
    return json.loads(ws.recv())

def main():
    ws = ws_connect()
    print("Подключено к MAX\n")

    # GET_CHATS
    chats = get_chats(ws)
    items = chats.get("payload", {}).get("items", [])
    print(f"=== ЧАТЫ ({len(items)}) ===\n")
    cid = None
    for c in items[:5]:
        name = c.get("name") or c.get("title", "(без названия)")
        print(f"  [{c['id']}] {name}")
        if not cid:
            cid = c["id"]
    if cid:
        print()
        # GET_HISTORY
        hist = get_history(ws, cid, 3)
        msgs = hist.get("payload", {}).get("items", [])
        print(f"=== ИСТОРИЯ чата [{cid}] (3 сообщ.) ===\n")
        for m in msgs:
            author = m.get("author", {}).get("name", "?")
            text = m.get("text", "")[:80]
            print(f"  {author}: {text}\n" if text else "  (вложение)\n")

        # MSG_SEND
        resp = send_message(ws, cid, "Привет! Это тест из example.py")
        mid = resp.get("payload", {}).get("id", "?")
        print(f"  Отправлено, id={mid}\n")
    ws.close()

if __name__ == "__main__":
    main()
