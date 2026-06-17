#!/usr/bin/env python3
"""Standalone MAX API client for opcode exploration — no MCP dependency."""
import json, os, ssl, time, sys
import requests as _requests
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())

CONFIG_PATH = os.path.expanduser("~/.max_config.json")
TOKEN = os.environ.get("MAX_ACCESS_TOKEN")
DEVICE_ID = os.environ.get("MAX_DEVICE_ID")
if not TOKEN or not DEVICE_ID:
    cfg = json.load(open(CONFIG_PATH))
    TOKEN = cfg["access_token"]
    DEVICE_ID = cfg["device_id"]

class MaxSession:
    def __init__(self, token, device_id):
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
        self.seq += 1
        self._send({"ver":11,"cmd":0,"seq":self.seq,"opcode":6,"payload":{
            "userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru",
                "osVersion":"Linux","deviceName":"Firefox",
                "headerUserAgent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0",
                "appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},
            "deviceId":self.device_id}})
        self.seq += 1
        self._send({"ver":11,"cmd":0,"seq":self.seq,"opcode":19,"payload":{
            "interactive":True,"token":self.token,
            "chatsCount":100,"chatsSync":100,"contactsSync":0,"presenceSync":0,"draftsSync":0}})
        for _ in range(5):
            r = self._recv(10)
            if r is None: continue
            if r.get("cmd")==3 and r.get("opcode")==19:
                raise RuntimeError(f"Login error: {r.get('payload')}")
            if r.get("cmd")==1 and r.get("opcode")==19:
                self._login_payload = r.get("payload",{}); return

    def request(self, opcode, payload, timeout=15):
        self.seq += 1
        self._send({"ver":11,"cmd":0,"seq":self.seq,"opcode":opcode,"payload":payload})
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = self._recv(5)
            if r is None: continue
            if r.get("cmd")==1 and r.get("seq")==self.seq: return r.get("payload",{})
            if r.get("cmd")==3 and r.get("seq")==self.seq:
                raise RuntimeError(f"Error: {r.get('payload')}")
        raise TimeoutError(f"Timeout on opcode {opcode}")

    def _send(self, d):
        if self.ws: self.ws.send(json.dumps(d))

    def _recv(self, timeout=5):
        if not self.ws: return None
        self.ws.settimeout(timeout)
        try:
            raw = self.ws.recv()
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def close(self):
        if self.ws:
            try: self.ws.close()
            except: pass

def main():
    sess = MaxSession(TOKEN, DEVICE_ID)
    try:
        sess.connect()
        print(f"✅ Connected. Session seq: {sess.seq}")
        profile = (sess._login_payload or {}).get("profile",{}).get("contact",{})
        names = [n.get("name","?") for n in profile.get("names",[])]
        print(f"👤 Logged in as: {', '.join(names) if names else 'unknown'}")

        chats = sess._login_payload.get("chats",[])
        print(f"\n📋 Chats ({len(chats)}):")
        for c in chats:
            print(f"  {c.get('id','?'):8} [{c.get('type','?'):7}] {c.get('title','') or c.get('name','')}")

        # ─── Opcode scan ─────────────────────────────────────────────────
        print("\n🔍 Scanning unexplored opcodes...")

        # Opcodes we know: 6,19,32,49,53,64,65,66,67,71,72,74,87,92,132,136,140,142
        # Let's check gaps and higher ranges
        known = {6,19,17,18,32,49,53,64,65,66,67,71,72,74,87,92,132,136,140,142}
        # Test ranges: 1-5, 7-16, 20-31, 33-48, 50-52, 54-63, 68-70, 73, 75-86, 88-91, 93-131, 133-135, 137-139, 141, 143-255

        interesting = []

        for op in range(1, 256):
            if op in known:
                continue
            # Skip high push notification numbers for now
            if op >= 130 and op <= 150:
                continue
            if op >= 200:  # Unlikely to be valid
                pass

            try:
                pl = {} if op not in [1,4,5] else {"ping": int(time.time()*1000)}
                if op >= 130:
                    pl = {"test": 1}
                resp = sess.request(op, pl, timeout=5)
                if resp:
                    pretty = json.dumps(resp, ensure_ascii=False)[:200]
                    line = f"  opcode {op:3d}: {pretty}"
                    print(line)
                    interesting.append((op, resp))
                else:
                    pass  # empty response = still interesting (ACK with no payload)
            except TimeoutError:
                pass  # timeout = no match
            except RuntimeError as e:
                err = str(e)[:100]
                print(f"  opcode {op:3d}: ❌ {err}")
                interesting.append((op, {"error": err}))

        print(f"\n✨ Interesting responses from {len(interesting)} opcodes")
        for op, resp in interesting:
            print(f"  {op}: {json.dumps(resp, ensure_ascii=False)[:300]}")

    finally:
        sess.close()

if __name__ == "__main__":
    main()
