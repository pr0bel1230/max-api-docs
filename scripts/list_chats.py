#!/usr/bin/env python3
"""List MAX chats to find Sasha Shipilova."""
import sys, os, importlib.util

sys.path.insert(0, os.path.dirname(__file__))
spec = importlib.util.spec_from_file_location('mcp_server',
    os.path.join(os.path.dirname(__file__), 'mcp-max-user-server.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

TOKEN = os.environ.get('MAX_ACCESS_TOKEN')
DEVICE_ID = os.environ.get('MAX_DEVICE_ID')

sess = mod.MaxSession(TOKEN, DEVICE_ID)
sess.connect()
print('✅ Connected')
chats = sess.get_chats()
for c in chats:
    print(f'  Chat {c.get("id", c.get("chatId"))}: [{c.get("type")}] {c.get("title", c.get("name"))}')
sess.close()
print('Done')
