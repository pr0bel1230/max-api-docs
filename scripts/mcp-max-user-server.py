#!/usr/bin/env python3
"""MCP сервер для MAX Messenger — отправка, получение и удаление от имени пользователя.

Использует WebSocket протокол MAX (как веб-версия web.max.ru).
Токены (access_token, device_id) читаются из переменных окружения:
    MAX_ACCESS_TOKEN, MAX_DEVICE_ID

Или из файла ~/.max_config.json, если токены через max_setup сохранены.
"""

import json
import os
import ssl
import time
from typing import Any
import requests as _requests
from mcp.server.fastmcp import FastMCP
from websocket import create_connection

import certifi
_ssl_ctx = ssl.create_default_context(cafile=certifi.where())

# ─── Configuration ───────────────────────────────────────────────────

def load_config() -> dict:
    """Читает конфиг из переменных окружения или файла."""
    cfg = {}
    token = os.environ.get("MAX_ACCESS_TOKEN") or os.environ.get("access_token")
    device_id = os.environ.get("MAX_DEVICE_ID") or os.environ.get("device_id")
    if token:
        cfg["access_token"] = token
    if device_id:
        cfg["device_id"] = device_id

    # fallback: файл
    config_file = os.path.expanduser("~/.max_config.json")
    if not cfg and os.path.exists(config_file):
        with open(config_file) as f:
            cfg = json.load(f)
    return cfg

def save_config(config: dict) -> None:
    config_file = os.path.expanduser("~/.max_config.json")
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# ─── MAX WebSocket Client ───────────────────────────────────────────

class MaxSession:
    """Временная WebSocket сессия: подключиться → запрос → ответ → отключиться."""

    def __init__(self, token: str, device_id: str):
        self.token = token
        self.device_id = device_id
        self.url = "wss://ws-api.oneme.ru/websocket"
        self.ws = None
        self.seq = 0
        self._login_payload = None

    def connect(self):
        headers = [
            "Origin: https://web.max.ru",
            "User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0"
        ]
        self.ws = create_connection(self.url, header=headers, timeout=10, sslopt={"context": _ssl_ctx})

        # INIT (opcode 6)
        self.seq += 1
        init = {
            "ver": 11, "cmd": 0, "seq": self.seq, "opcode": 6,
            "payload": {
                "userAgent": {
                    "deviceType": "WEB", "locale": "ru", "deviceLocale": "ru",
                    "osVersion": "Linux", "deviceName": "Firefox",
                    "headerUserAgent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0",
                    "appVersion": "25.11.1", "screen": "1080x1920 1.0x",
                    "timezone": "Asia/Yekaterinburg"
                },
                "deviceId": self.device_id
            }
        }
        self._send(init)

        # LOGIN (opcode 19)
        self.seq += 1
        login = {
            "ver": 11, "cmd": 0, "seq": self.seq, "opcode": 19,
            "payload": {
                "interactive": True,
                "token": self.token,
                "chatsCount": 100, "chatsSync": 100,
                "contactsSync": 0, "presenceSync": 0, "draftsSync": 0
            }
        }
        self._send(login)

        for _ in range(5):
            resp = self._recv(timeout=10)
            if resp is None:
                continue
            cmd = resp.get("cmd")
            opcode = resp.get("opcode")
            if cmd == 3 and opcode == 19:
                self.close()
                raise RuntimeError(f"MAX login error: {resp.get('payload', {})}")
            if cmd == 1 and opcode == 19:
                self._login_payload = resp.get("payload", {})
                break

    def request(self, opcode: int, payload: dict, timeout: float = 15.0) -> Any:
        self.seq += 1
        msg = {"ver": 11, "cmd": 0, "seq": self.seq, "opcode": opcode, "payload": payload}
        self._send(msg)

        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = self._recv(timeout=5)
            if resp is None:
                continue
            cmd = resp.get("cmd")
            if cmd == 1 and resp.get("seq") == self.seq:
                return resp.get("payload", {})
            if cmd == 3 and resp.get("seq") == self.seq:
                raise RuntimeError(f"MAX error: {resp.get('payload', {})}")

        raise TimeoutError("MAX API timeout")

    def send_message(self, chat_id: int, text: str) -> dict:
        return self.request(64, {
            "chatId": chat_id,
            "message": {
                "text": text,
                "cid": int(time.time() * 1000),
                "elements": [],
                "attaches": []
            },
            "notify": True
        })

    def upload_and_send_file(self, chat_id: int, text: str, file_path: str) -> dict:
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_name)[1].lstrip(".") or "bin"

        resp = self.request(87, {"name": file_name, "size": file_size, "ext": ext, "count": 1})
        info = resp.get("info", [{}])[0]
        upload_url = info["url"]
        file_id = info["fileId"]
        file_token = info["token"]

        with open(file_path, "rb") as f:
            http_resp = _requests.post(upload_url, files={"file": (file_name, f, "application/octet-stream")})
        if http_resp.status_code != 200:
            raise RuntimeError(f"Upload failed: HTTP {http_resp.status_code}")

        deadline = time.time() + 30
        found = False
        while time.time() < deadline:
            evt = self._recv(timeout=5)
            if evt and evt.get("opcode") == 136:
                found = True
                break
        if not found:
            raise TimeoutError("MAX: attach confirmation timeout")

        msg_payload = {
            "chatId": chat_id,
            "message": {
                "text": text,
                "cid": int(time.time() * 1000),
                "elements": [],
                "attaches": [{
                    "_type": "FILE",
                    "fileId": file_id,
                    "token": file_token,
                    "name": file_name,
                    "size": file_size
                }]
            },
            "notify": True
        }
        return self.request(64, msg_payload)

    def get_history(self, chat_id: int, count: int = 10) -> list[dict]:
        resp = self.request(49, {
            "chatId": chat_id,
            "forward": 0,
            "backward": count,
            "backwardTime": 0,
            "forwardTime": 0,
            "getChat": False,
            "from": int(time.time() * 1000),
            "getMessages": True,
            "interactive": False,
        })
        return resp.get("messages", [])

    def get_chats(self) -> list[dict]:
        if self._login_payload:
            return self._login_payload.get("chats", [])
        resp = self.request(53, {"count": 100, "marker": 0})
        return resp.get("chats", [])

    def get_profile(self) -> dict | None:
        return self._login_payload.get("profile", {}) if self._login_payload else None

    def get_contact_info(self, user_id: int) -> dict:
        resp = self.request(32, {"contactIds": [user_id]})
        contacts = resp.get("contacts", [])
        return contacts[0] if contacts else {}

    def _send(self, data: dict):
        if self.ws:
            self.ws.send(json.dumps(data))

    def _recv(self, timeout: float = 5.0) -> dict | None:
        if not self.ws:
            return None
        self.ws.settimeout(timeout)
        try:
            raw = self.ws.recv()
            if raw:
                return json.loads(raw)
        except Exception:
            return None
        return None

    def close(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass


def max_session(opener=lambda c: c, timeout: float = 15.0):
    config = load_config()
    token = config.get("access_token")
    device_id = config.get("device_id")
    if not token or not device_id:
        raise RuntimeError(
            "MAX не настроен.\n"
            "Укажи переменные окружения MAX_ACCESS_TOKEN и MAX_DEVICE_ID,\n"
            "или используй инструмент max_setup."
        )
    session = MaxSession(token, device_id)
    try:
        session.connect()
        return opener(session)
    finally:
        session.close()


# ─── MCP Server ──────────────────────────────────────────────────────

mcp = FastMCP("MAX Messenger (User)", instructions="Работа с MAX Messenger от имени пользователя через WebSocket API.")

@mcp.tool()
def max_setup(token: str, device_id: str) -> str:
    """Настроить MAX: сохранить token и deviceId.

    Args:
        token: Токен сессии (из web.max.ru → F12 → WS → opcode 19)
        device_id: ID устройства (из INIT → opcode 6)
    """
    config = load_config()
    config["access_token"] = token
    config["device_id"] = device_id
    save_config(config)
    return "✅ MAX настроен."

@mcp.tool()
def max_test() -> str:
    """Проверить подключение к MAX (профиль, чаты)."""
    try:
        def test(s):
            contact = (s.get_profile() or {}).get("contact", {})
            names = contact.get("names", [])
            names_str = ", ".join(n.get("name", "?") for n in names)
            chats_count = len(s.get_chats())
            return f"✅ MAX: {names_str}, чатов: {chats_count}"
        return max_session(test)
    except TimeoutError:
        return "❌ Таймаут. Обнови токен."
    except Exception as e:
        return f"❌ {e}"

def _json(result) -> str:
    return json.dumps(result, ensure_ascii=False, default=str)

@mcp.tool()
def max_get_chats() -> str:
    """Получить список чатов."""
    try:
        def get_chats(s):
            chats = s.get_chats()
            return [{
                "id": c.get("id", c.get("chatId")),
                "title": c.get("title", c.get("name", "")),
                "type": c.get("type", ""),
                "last_message": c.get("lastMessage", {}).get("text", ""),
                "unread_count": c.get("newMessages", 0),
            } for c in chats]
        return _json(max_session(get_chats))
    except Exception as e:
        return _json({"error": str(e)})

@mcp.tool()
def max_get_messages(chat_id: int | None = None, count: int = 10) -> str:
    """Получить последние сообщения из чата MAX."""
    config = load_config()
    cid = chat_id or config.get("default_chat_id")
    if not cid:
        return _json({"error": "ID чата не указан."})
    count = max(1, min(50, count))

    try:
        def get_msgs(s):
            msgs = s.get_history(cid, count)
            return [{
                "id": m.get("id"),
                "sender": m.get("sender"),
                "text": m.get("text", ""),
                "timestamp": m.get("time", m.get("timestamp", 0)),
                "type": m.get("type", "text"),
                "attachments": m.get("attaches", []),
            } for m in msgs]
        return _json(max_session(get_msgs))
    except Exception as e:
        return _json({"error": str(e)})

@mcp.tool()
def max_send_message(chat_id: int | None = None, text: str = "") -> str:
    """Отправить сообщение в чат MAX."""
    config = load_config()
    cid = chat_id or config.get("default_chat_id")
    if not cid:
        return _json({"error": "ID чата не указан."})
    if not text:
        return _json({"error": "Текст не может быть пустым."})

    try:
        def send(s):
            resp = s.send_message(cid, text)
            msg_id = resp.get("id", resp.get("messageId"))
            return {"success": True, "chat_id": cid, "message_id": msg_id, "text_preview": text[:80]}
        return _json(max_session(send))
    except Exception as e:
        return _json({"error": str(e)})

@mcp.tool()
def max_delete_message(chat_id: int | None = None, message_id: int = 0, for_me: bool = False) -> str:
    """Удалить сообщение в чате MAX.

    Внимание: использует opcode 66 (MSG_DELETE). Не 65!
    """
    config = load_config()
    cid = chat_id or config.get("default_chat_id")
    if not cid:
        return _json({"error": "ID чата не указан."})
    if not message_id:
        return _json({"error": "ID сообщения не указан."})

    try:
        def delete_msg(s):
            resp = s.request(66, {"chatId": cid, "messageIds": [message_id], "forMe": for_me})
            return {"success": True, "chat_id": cid, "message_id": message_id}
        return _json(max_session(delete_msg))
    except Exception as e:
        return _json({"error": str(e)})

@mcp.tool()
def max_send_file(chat_id: int | None = None, text: str = "", file_path: str = "") -> str:
    """Отправить файл с текстом в чат MAX."""
    config = load_config()
    cid = chat_id or config.get("default_chat_id")
    if not cid:
        return _json({"error": "ID чата не указан."})
    if not file_path:
        return _json({"error": "Путь к файлу не указан."})

    full_path = os.path.expanduser(file_path)
    if not os.path.exists(full_path):
        return _json({"error": f"Файл не найден: {full_path}"})

    try:
        def send_file(s):
            resp = s.upload_and_send_file(cid, text, full_path)
            msg_id = resp.get("id", resp.get("messageId"))
            return {
                "success": True,
                "chat_id": cid,
                "message_id": msg_id,
                "file": os.path.basename(full_path),
            }
        return _json(max_session(send_file))
    except Exception as e:
        return _json({"error": str(e)})

@mcp.tool()
def max_set_default_chat(chat_id: int) -> str:
    """Установить ID чата по умолчанию."""
    config = load_config()
    config["default_chat_id"] = chat_id
    save_config(config)
    return f"✅ Чат {chat_id} сохранён."


if __name__ == "__main__":
    mcp.run(transport="stdio")
