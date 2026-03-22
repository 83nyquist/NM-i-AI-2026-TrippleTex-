import urllib.request
import json
import ssl
import sys
import threading
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://mcp-docs.ainm.no/mcp"

# 1. Initialize to get session ID
init_payload = {
    "jsonrpc": "2.0", 
    "id": 1, 
    "method": "initialize", 
    "params": {
        "protocolVersion": "2024-11-05", 
        "capabilities": {}, 
        "clientInfo": { "name": "python", "version": "1.0.0" }
    }
}
req = urllib.request.Request(url, data=json.dumps(init_payload).encode('utf-8'), method='POST')
req.add_header('Content-Type', 'application/json')
req.add_header('Accept', 'application/json, text/event-stream')

resp = urllib.request.urlopen(req, context=ctx)
session_id = resp.getheader('mcp-session-id')

def read_sse(resp):
    try:
        for line in resp: pass
    except: pass

t = threading.Thread(target=read_sse, args=(resp,))
t.daemon = True
t.start()
time.sleep(1)

tool_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}
req3 = urllib.request.Request(url, data=json.dumps(tool_payload).encode('utf-8'), method='POST')
req3.add_header('Content-Type', 'application/json')
req3.add_header('Accept', 'application/json, text/event-stream')
req3.add_header('mcp-session-id', session_id)

try:
    resp3 = urllib.request.urlopen(req3, context=ctx)
    print("--- RESULTS FOR tools/list ---")
    print(resp3.read().decode())
except Exception as e:
    print(f"Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())

time.sleep(1)
