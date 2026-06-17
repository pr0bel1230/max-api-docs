#!/usr/bin/env /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""
Final probes: each probe = fresh connection, single request.
"""
import json, ssl, time, os
import certifi
from websocket import create_connection

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
_cfg = json.load(open(os.path.expanduser("~/claude-home/config/max_config.json")))
TOKEN, DID = _cfg["access_token"], _cfg["device_id"]
SASHA = 7268926
NOW = int(time.time()*1000)

G="\033[92m";Y="\033[93m";R="\033[91m";C="\033[96m";B="\033[1m";N="\033[0m"

def probe(op, pl):
    ws = create_connection("wss://ws-api.oneme.ru/websocket",
        header=["Origin: https://web.max.ru"], timeout=15, sslopt={"context":_ssl_ctx})
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":1,"opcode":6,"payload":{"userAgent":{"deviceType":"WEB"},"deviceId":DID}}))
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":2,"opcode":19,"payload":{"interactive":True,"token":TOKEN,"chatsCount":1,"chatsSync":1,"contactsSync":0,"presenceSync":0,"draftsSync":0}}))
    for _ in range(10):
        r = json.loads(ws.recv())
        if r.get("opcode")==19: break  # consume LOGIN response
    ws.send(json.dumps({"ver":11,"cmd":0,"seq":3,"opcode":op,"payload":pl}))
    result = None
    d = time.time()+15
    while time.time()<d:
        try:
            r = json.loads(ws.recv())
            if r.get("cmd")==0: continue
            if r.get("seq")==3:
                result = r; break
        except:
            break
    ws.close()
    return result

def show(r):
    if r is None: return f"{Y}TIMEOUT{N}"
    if r.get("cmd")==1:
        p = r.get("payload",{})
        j = json.dumps(p, ensure_ascii=False)[:600] if p else "null"
        return f"{G}ACK{N} {j}"
    if r.get("cmd")==3:
        e = r.get("payload",{})
        return f"{R}ERR{N} {(e.get('message') or e.get('error') or str(e))[:200]}"
    return str(r)[:200]

# 1. OPCODE 92 with messageIds (delete?)
print(f"{B}1. OP92 — messageIds variant{N}")
for pl, label in [
    ({"chatId":SASHA, "messageIds":["116483269189784770"], "forMe":True}, "messageIds forMe"),
    ({"chatId":SASHA, "messageIds":["116483269189784770"]}, "messageIds no forMe"),
    ({"chatId":SASHA, "messageIds":["116483269189784770","116483218864569532"]}, "multiple messageIds"),
]:
    r = probe(92, pl)
    print(f"  {label:<35s} → {show(r)}")
    time.sleep(0.3)

# 2. OPCODE 55 — what does it do?
print(f"\n{B}2. OP55 — mystery{N}")
for pl, label in [
    ({}, "empty"),
    ({"chatId":SASHA}, "chatId"),
    ({"chatId":SASHA, "marker":0, "count":10}, "full pagination"),
    ({"query":"test"}, "query"),
]:
    r = probe(55, pl)
    print(f"  {label:<25s} → {show(r)}")
    time.sleep(0.3)

# 3. OPCODE 272 with different chats/folders
print(f"\n{B}3. OP272 — folders with different payloads{N}")
for pl, label in [
    ({"chatId":SASHA}, "chatId=SASHA"),
    ({"chatId":SASHA, "folderSync":NOW-100000}, "with folderSync"),
]:
    r = probe(272, pl)
    print(f"  {label:<30s} → {show(r)}")
    time.sleep(0.3)

# 4. IMAGE_UPLOAD — what's the difference between 80 and 81?
print(f"\n{B}4. Image upload — 80 vs 81{N}")
for op in [80, 81]:
    r = probe(op, {"count": 1, "photoIds": ["test"]})
    print(f"  [{op}] photoIds=test: {show(r)}")
    time.sleep(0.3)

# 5. OPCODE 100 — still void ACK with non-null payload?
print(f"\n{B}5. OP100 — void ACK?{N}")
r = probe(100, {"debug": True})
print(f"  debug=True: {show(r)}")

# 6. OPCODE 201 — try with userIds as object
print(f"\n{B}6. OP201 — users with typed field{N}")
for pl, label in [
    ({"userIds":[]}, "empty array"),
    ({"userIds":["3260455"]}, "str array"),
    ({"userIds":[3260455], "version":"new"}, "with version"),
]:
    r = probe(201, pl)
    print(f"  {label:<25s} → {show(r)}")
    time.sleep(0.3)

# 7. Quick retest: opcodes 55-62 with chatId only
print(f"\n{B}7. Quick scan 55-62 with chatId{N}")
for op in range(55, 63):
    r = probe(op, {"chatId": SASHA})
    cmd = r.get("cmd") if r else "timeout"
    if cmd == 1:
        pl = r.get("payload", {})
        if pl and pl != {}:
            s = json.dumps(pl, ensure_ascii=False)[:200]
            print(f"  [{op}] non-empty: {s}")
        else:
            print(f"  [{op}] ACK null")
    elif cmd == 3:
        e = r.get("payload", {})
        print(f"  [{op}] {R}ERR{N}: {(e.get('message') or e.get('error') or str(e))[:100]}")
    time.sleep(0.2)

print(f"\n{G}{B}DONE{N}")
