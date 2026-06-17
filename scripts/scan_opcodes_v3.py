#!/usr/bin/env python3
"""
MAX API Opcode Scanner v3.
Resilient scanning — survives connection drops.
"""
import json, ssl, time, os, sys
import certifi
from websocket import create_connection, WebSocketConnectionClosedException

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())

TOKEN = "An_Sx6HQ9HDiysAYdnqjFmqfxRg9Zugl1JzuC5CMSfQ8edqCCcBLi97RpVtQAmf3rUjG5DPcIdQ2sB-fA-DraQLCbjr0qqoj0AYXhDTyGRWMnNjtdsTMU3KHwtuKjHRu-X56qxOXxbuioH8rVlm7XC9Z356eYtedGzWY3sAVXApVfG5tGpf-s2mBRMI5cf_QfrLL3Ux3TXF4O_oWoigpNj86KsXhx_6Ycr1IxApx-lQgQv72gLesh0r2BupKdHU0I52s63QqDseV5EgNVqAHad0LdPTcK9u7SEWP3BlxNTwSYk6Ei4twExVfFPrG3aW4LVKYfMpC_wTE1Q5CtONnV6UdohsqM5xhxvxK-UPCB320JdBXD0PQRWps5K6UQ3T34y7O7T_INYRRSvEwcX-llH7KHcms8lb4lebwacSSn3FuKvscR3xBKxraO7VbxCwFv_AsVFINyfHt9DlxPIQfvKeGJNtRSUFFL3POFZ8XYWlu7fMN5ssqSFCxzq1nQm62sY-xP4R1pDkhl5Rc07OVpFl7BOe-C3XKUCkujZFwowycfSvZo8auAKRFkMeeXwIYMZkthLhykwj4htuKQe8mPqNBSnfvrdmWOVgMvetue6dIRoe-XLac3a8-OWSnkjRzgpPPxxIWoVacx7VxAkSjnK0EzbDrFhSjJVQpKY6q-2LllIwU-Q8jve_wyU3c0ZDCi6AS-Gg"
DID = "0a531fd8-6517-401a-990a-45fb6901a544"

class Session:
    def __init__(self):
        self.ws = None
        self.seq = 0

    def connect(self):
        self.close()
        self.ws = create_connection(
            "wss://ws-api.oneme.ru/websocket",
            header=["Origin: https://web.max.ru", "User-Agent: Mozilla/5.0"],
            timeout=10, sslopt={"context": _ssl_ctx})
        self.seq += 1
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":6,"payload":{
            "userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru",
                "osVersion":"Linux","deviceName":"Firefox",
                "headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1",
                "screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},
            "deviceId":DID}}))
        self.seq += 1
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":19,"payload":{
            "interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0}}))
        for _ in range(8):
            r = self._recv(10)
            if r and r.get("cmd")==1 and r.get("opcode")==19: return
        raise RuntimeError("login failed")

    def request(self, opcode, payload, timeout=8):
        self.seq += 1
        msg = json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":opcode,"payload":payload})
        try:
            self.ws.send(msg)
        except WebSocketConnectionClosedException:
            return "dead", None
        except Exception as e:
            return "dead", None
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                r = self._recv(3)
                if r is None:
                    continue
                if r.get("cmd") == 1 and r.get("seq") == self.seq:
                    return "ack", r.get("payload", {})
                if r.get("cmd") == 3 and r.get("seq") == self.seq:
                    err = r.get("payload", {})
                    txt = err.get("message", str(err)[:200]) if isinstance(err, dict) else str(err)[:200]
                    return "error", txt
        except WebSocketConnectionClosedException:
            return "dead", None
        return "timeout", None

    def _recv(self, t=3):
        if not self.ws: return None
        self.ws.settimeout(t)
        try:
            r = self.ws.recv()
            return json.loads(r) if r else None
        except: return None

    def close(self):
        if self.ws:
            try: self.ws.close()
            except: pass
            self.ws = None

KNOWN_OPS = {6,19,32,49,53,64,65,66,67,71,72,74,87,92,132,136,140,142}
SASHA_CHAT = 7268926

def scan():
    sess = Session()
    sess.connect()
    print("✅ Connected\n")

    data_acks = []
    empty_acks = []
    errors = []
    timeouts = []

    for op in range(1, 200):
        if op in KNOWN_OPS: continue
        if 130 <= op <= 150: continue

        payload = {}
        if op == 5:
            payload = {"events": [{"type": "typing", "chatId": SASHA_CHAT}]}

        cat, result = sess.request(op, payload)
        if cat == "dead":
            print(f"  ♻️  Reconnecting at op {op}...")
            sess.connect()
            cat, result = sess.request(op, payload)
            if cat == "dead":
                print(f"  ❌ Still dead at {op}, aborting")
                break

        if cat == "ack":
            if result:
                data_acks.append((op, result))
                print(f"  ✅ {op:3d}: {json.dumps(result, ensure_ascii=False)[:160]}")
            else:
                empty_acks.append(op)
                if len(empty_acks) % 10 == 1:
                    print(f"  ⬜ {op:3d}: empty ACK (total: {len(empty_acks)})")
        elif cat == "error":
            errors.append((op, result))
            print(f"  ❌ {op:3d}: {result[:120]}")
        else:
            timeouts.append(op)
            if len(timeouts) % 20 == 1:
                print(f"  ⏰ {op:3d}: timeout (total: {len(timeouts)})")

    sess.close()

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"  ✅ Data: {len(data_acks)}")
    print(f"  ⬜ Empty: {len(empty_acks)}")
    print(f"  ❌ Errors: {len(errors)}")
    print(f"  ⏰ Timeouts: {len(timeouts)}")

    for op, data in data_acks:
        print(f"\n{'─'*40}")
        print(f"  OPCODE {op}:")
        print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")

    for op, err in errors:
        print(f"\n{'─'*40}")
        print(f"  OPCODE {op}: ERROR — {err[:120]}")

if __name__ == "__main__":
    scan()
