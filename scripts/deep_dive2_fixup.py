#!/usr/bin/env /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""
Quick follow-up probes from deep_dive2 findings.
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926
MY_UID = 3260455

G="\033[92m";Y="\033[93m";R="\033[91m";C="\033[96m";B="\033[1m";N="\033[0m"
_ok=lambda r:r and r.get("cmd")==1

class Session:
    def __init__(self):
        self.ws,self.seq=None,0
    def connect(self):
        self.ws=create_connection("wss://ws-api.oneme.ru/websocket",header=["Origin: https://web.max.ru","User-Agent: Mozilla/5.0"],timeout=15,sslopt={"context":_ssl_ctx})
        self.seq+=1;self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":6,"payload":{"userAgent":{"deviceType":"WEB","locale":"ru","deviceLocale":"ru","osVersion":"Linux","deviceName":"Firefox","headerUserAgent":"Mozilla/5.0","appVersion":"25.11.1","screen":"1080x1920 1.0x","timezone":"Asia/Yekaterinburg"},"deviceId":DID}}))
        self.seq+=1;self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":self.seq,"opcode":19,"payload":{"interactive":True,"token":TOKEN,"chatsCount":10,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0}}))
        for _ in range(10):
            r=self._r(10)
            if _ok(r) and r.get("opcode")==19:return True
            if r and r.get("cmd")==3 and r.get("opcode")==19:return False
        return False
    def req(self,op,pl,t=20):
        self.seq+=1;rid=self.seq
        self.ws.send(json.dumps({"ver":11,"cmd":0,"seq":rid,"opcode":op,"payload":pl}))
        d=time.time()+t
        while time.time()<d:
            r=self._r(8)
            if r:
                if r.get("cmd")==0:continue
                if r.get("seq")==rid:return r
        return None
    def _r(self,t=5):
        if not self.ws:return None
        self.ws.settimeout(t)
        try:r=self.ws.recv();return json.loads(r)if r else None
        except:return None
    def close(self):
        if self.ws:
            try:self.ws.close()
            except:pass

def probe(op,pl,t=20):
    s=Session()
    try:
        if not s.connect():return None
        return s.req(op,pl,t)
    except:return None
    finally:s.close()

def label(r):
    if r is None:return f"{Y}TIMEOUT{N}"
    if r.get("cmd")==1:
        pl=r.get("payload",{})
        j=json.dumps(pl,ensure_ascii=False,indent=2)[:600] if pl else "null"
        return f"{G}ACK{N}\n"+ind(j,4)
    if r.get("cmd")==3:
        e=r.get("payload",{});m=(e.get("message")or e.get("error")or str(e))[:300]
        return f"{R}ERR{N} {m}"
    return str(r)[:200]

def ind(s,n):return "\n".join(" "*n+l if l.strip()else l for l in s.split("\n"))

print(f"{B}{C}🔍 Follow-up probes{N}\n")

# ──────────────────────────────────────────────────
# 1. GET_CHATS + GET_HISTORY double check
# ──────────────────────────────────────────────────
print(f"{B}1. GET_CHATS (53) + GET_HISTORY (49) double check{N}")

s=Session()
s.connect()

# GET_CHATS
chats_r = s.req(53, {"count":10,"marker":0})
if _ok(chats_r):
    chats = chats_r.get("payload",{}).get("chats",[])
    print(f"\n  Чатов получено: {len(chats)}")
    for c in chats:
        print(f"    id={c.get('id')} title=\"{c.get('title','')}\" type={c.get('type')} lastMsg=\"{c.get('lastMessage',{}).get('text','')[:50]}\"")
    # Check if SASHA chat exists
    found_sasha = any(c.get("id")==SASHA for c in chats)
    print(f"  Чат {SASHA}: {'✅ найден' if found_sasha else '❌ НЕ НАЙДЕН!'}")

# GET_HISTORY with all possible fields
for pl, label_t in [
    ({"chatId":SASHA,"backward":5,"getMessages":True,"getChat":True},"with getChat"),
    ({"chatId":SASHA,"backward":5,"getMessages":True},"standard"),
    ({"chatId":SASHA,"backward":10,"getMessages":True,"from":0},"from=0"),
]:
    r = s.req(49, pl)
    if _ok(r):
        pl2 = r.get("payload",{})
        msgs = pl2.get("messages",[])
        print(f"\n  GET_HISTORY {label_t:<20s}: {len(msgs)} сообщений")
        if msgs:
            for m in msgs[:3]:
                print(f"    id={m.get('id')} text=\"{m.get('text','')[:60]}\"")
            if "chat" in pl2:
                print(f"    chat info: {json.dumps(pl2.get('chat',{}),ensure_ascii=False)[:200]}")
    else:
        print(f"\n  GET_HISTORY {label_t:<20s}: {label(r)}")
s.close()

# ──────────────────────────────────────────────────
# 2. OPCODE 92 with startTime
# ──────────────────────────────────────────────────
print(f"\n\n{B}2. OPCODE 92 with startTime+endTime{N}")
now=int(time.time()*1000)
for pl,lb in [
    ({"chatId":SASHA,"startTime":0,"endTime":now},"start=0 end=now"),
    ({"chatId":SASHA,"startTime":0,"endTime":now,"forMe":True},"+forMe"),
    ({"chatId":SASHA,"startTime":now-86400000,"endTime":now},"last 24h"),
]:
    r=probe(92,pl)
    print(f"  {lb:<35s} → {label(r)}")

# ──────────────────────────────────────────────────
# 3. OPCODE 86 with boolean show
# ──────────────────────────────────────────────────
print(f"\n\n{B}3. OPCODE 86 with boolean show{N}")
for pl,lb in [
    ({"chatId":SASHA,"show":True},"show=True"),
    ({"chatId":SASHA,"show":False},"show=False"),
    ({"show":True},"show=True no chatId"),
    ({"show":True,"count":50},"show=True count=50"),
]:
    r=probe(86,pl)
    print(f"  {lb:<30s} → {label(r)}")

# ──────────────────────────────────────────────────
# 4. OPCODE 201 with different payload fields
# ──────────────────────────────────────────────────
print(f"\n\n{B}4. OPCODE 201 — users (different fields){N}")
for pl,lb in [
    ({"userIds":[MY_UID]},"userIds=[]"),
    ({"ids":[MY_UID,6236697]},"ids=[]"),
    ({"userId":MY_UID},"userId=int"),
    ({"userIds":[str(MY_UID)]},"userIds str"),
    ({"userIds":f"{MY_UID},{6236697}"},"userIds csv"),
    ({"id":MY_UID},"id=int"),
]:
    r=probe(201,pl)
    print(f"  {lb:<25s} → {label(r)}")

# ──────────────────────────────────────────────────
# 5. OPCODE 75 with fresh messageId
# ──────────────────────────────────────────────────
print(f"\n\n{B}5. OPCODE 75 — reaction with fresh msg{N}")
s=Session()
s.connect()

# Try getting a real message
hist_r=s.req(49,{"chatId":SASHA,"backward":5,"getMessages":True,"getChat":True})
if _ok(hist_r):
    msgs=hist_r.get("payload",{}).get("messages",[])
    print(f"  В истории: {len(msgs)} сообщений")
    if msgs:
        mid=str(msgs[0].get("id",""))
        print(f"  Первое сообщение: id={mid}")

        # Now try 75 with this real ID
        r75_1=probe(75,{"chatId":SASHA,"messageId":mid,"emoji":"👍"})
        print(f"  75 emoji='👍': {label(r75_1)}")

        r75_2=probe(75,{"chatId":SASHA,"messageId":mid,"reactionType":"LIKE"})
        print(f"  75 reactionType=LIKE: {label(r75_2)}")
    else:
        print(f"  {Y}Нет сообщений для теста{N}")

        # Maybe the chat doesn't exist? Try chat 0 or known chat from list
        hist2=s.req(49,{"chatId":SASHA,"backward":1,"getMessages":True})
        print(f"  Повторная попытка: {label(hist2)}")
else:
    print(f"  Получение истории: {label(hist_r)}")
s.close()

# ──────────────────────────────────────────────────
# 6. OPCODE 90 with real messageId
# ──────────────────────────────────────────────────
print(f"\n\n{B}6. OPCODE 90 — with messageId{N}")
s=Session()
s.connect()
hist_r=s.req(49,{"chatId":SASHA,"backward":1,"getMessages":True})
if _ok(hist_r):
    msgs=hist_r.get("payload",{}).get("messages",[])
    if msgs:
        mid=str(msgs[0].get("id",""))
        for pl,lb in [
            ({"chatId":SASHA,"messageId":mid},"minimal"),
            ({"chatId":SASHA,"messageId":mid,"count":5},"with count"),
        ]:
            r=probe(90,pl)
            print(f"  {lb:<25s} → {label(r)}")
    else:
        print(f"  {Y}Нет сообщений{N}")
else:
    print(f"  История не получена: {label(hist_r)}")
s.close()

# ──────────────────────────────────────────────────
# 7. Opcode 272 with just chatId (re-check structure)
# ──────────────────────────────────────────────────
print(f"\n\n{B}7. OPCODE 272 — full folder structure{N}")
r=probe(272,{"chatId":SASHA})
if _ok(r):
    pl=r.get("payload",{})
    print(f"  folderSync: {pl.get('folderSync')}")
    print(f"  foldersOrder ({len(pl.get('foldersOrder',[]))}): {pl.get('foldersOrder')}")
    for f in pl.get("folders",[]):
        print(f"  - id={f.get('id')} title=\"{f.get('title')}\" srcId={f.get('sourceId')}")
        print(f"    include={f.get('include')}")
        print(f"    filters={f.get('filters')}")
        if "filterSubjects" in f:
            print(f"    filterSubjects={json.dumps(f['filterSubjects'],ensure_ascii=False)[:200]}")
        if "elements" in f:
            print(f"    elements({len(f.get('elements',[]))}): {json.dumps(f['elements'][:2],ensure_ascii=False)[:200]}")
        if "options" in f:
            print(f"    options={f.get('options')}")
        if "updateTime" in f:
            print(f"    updateTime={f.get('updateTime')}")
else:
    print(f"  {label(r)}")

print(f"\n{B}{C}🏁 DONE{N}")
