#!/usr/bin/env python3
"""Quick MAX connection — list chats + targeted opcode scan."""
import json, os, ssl, time
import requests as _requests
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())

TOKEN = os.environ.get("MAX_ACCESS_TOKEN")
DEVICE_ID = os.environ.get("MAX_DEVICE_ID")
if not TOKEN or not DEVICE_ID:
    cfg = json.load(open(os.path.expanduser("~/.max_config.json")))
    TOKEN = cfg["access_token"]
    DEVICE_ID = cfg["device_id"]

class MaxSession:
    def __init__(self, token, device_id):
        self.token, self.device_id = token, device_id
        self.url = "wss://ws-api.oneme.ru/websocket"
        self.ws = None
        self.seq = 0
        self._login = None

    def connect(self):
        h = ["Origin: https://web.max.ru","User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0"]
        self.ws = create_connection(self.url, header=h, timeout=10, sslopt={"context":_ssl_ctx})
        self.seq += 1
        self._send({"ver":11,"cmd":0,"seq":self.seq,"opcode":6,"payload":{"userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},"deviceId":self.device_id}})
        self.seq += 1
        self._send({"ver":11,"cmd":0,"seq":self.seq,"opcode":19,"payload":{"interactive":True,"token":self.token,"chatsCount":100,"chatsSync":100,"contactsSync":0,"presenceSync":0,"draftsSync":0}})
        for _ in range(5):
            r = self._recv(10)
            if r is None: continue
            if r.get("cmd")==3 and r.get("opcode")==19: raise RuntimeError(f"Login error: {r.get('payload')}")
            if r.get("cmd")==1 and r.get("opcode")==19: self._login=r.get("payload",{}); return

    def request(self, opcode, payload, timeout=8):
        self.seq += 1
        self._send({"ver":11,"cmd":0,"seq":self.seq,"opcode":opcode,"payload":payload})
        deadline = time.time()+timeout
        while time.time()<deadline:
            r=self._recv(5)
            if r is None: continue
            if r.get("cmd")==1 and r.get("seq")==self.seq: return r.get("payload",{})
            if r.get("cmd")==3 and r.get("seq")==self.seq: raise RuntimeError(json.dumps(r.get("payload"),ensure_ascii=False)[:200])
        raise TimeoutError

    def _send(self,d): self.ws and self.ws.send(json.dumps(d))
    def _recv(self,t=5):
        self.ws.settimeout(t)
        try: r=self.ws.recv(); return json.loads(r) if r else None
        except: return None
    def close(self):
        if self.ws:
            try: self.ws.close()
            except: pass

sess=MaxSession(TOKEN,DEVICE_ID)
try:
    sess.connect()
    profile=(sess._login or {}).get("profile",{}).get("contact",{})
    names=[n.get("name","?") for n in profile.get("names",[])]
    print(f"👤 {', '.join(names)}")

    chats=sess._login.get("chats",[])
    print(f"\n📋 Chats ({len(chats)}):")
    for c in chats:
        print(f"  {c.get('id','?'):>8} [{c.get('type','?'):7}] {c.get('title','') or c.get('name','')}")

    # Scan promising opcodes (skip known ones)
    print("\n🔍 Scanning opcodes...")
    known={6,19,32,49,53,64,65,66,67,71,72,74,87,92,132,136,140,142}

    # Quick batch: opcodes 1-18, 20-31, 33-48, 50-52, 54-63, 68-70, 73, 75-86, 88-91
    scan=list(range(1,6))+list(range(7,16))+list(range(20,32))+list(range(33,49))+list(range(50,53))+list(range(54,64))+[68,69,70,73]+list(range(75,87))+list(range(88,92))+[93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,131,133,134,135,137,138,139,141,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,197,198,199]

    results=[]
    for op in scan:
        if op in known: continue
        try:
            if op in [1,2,3,4,5]:
                resp=sess.request(op,{"ping":int(time.time()*1000)},timeout=5)
            else:
                resp=sess.request(op,{},timeout=5)
            if resp:
                print(f"✅ opcode {op:3d}: {json.dumps(resp,ensure_ascii=False)[:150]}")
                results.append((op,resp))
            else:
                pass  # empty ACK — not interesting
        except TimeoutError: pass
        except RuntimeError as e:
            print(f"❌ opcode {op:3d}: {str(e)[:100]}")

    print(f"\n✨ Found {len(results)} responsive opcodes")
    for op,resp in results:
        print(f"  {op:3d}: {json.dumps(resp,ensure_ascii=False)[:200]}")
finally:
    sess.close()
