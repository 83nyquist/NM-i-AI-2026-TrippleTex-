import urllib.request
import json
import ssl
import sys
import threading

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

session_id = None
try:
    resp = urllib.request.urlopen(req, context=ctx)
    session_id = resp.getheader('mcp-session-id')
    print("Got session ID:", session_id)
except Exception as e:
    print("Error initializing:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())
    sys.exit(1)

def read_sse(resp):
    for line in resp:
        try:
            line = line.decode('utf-8')
            print("SSE LINE:", repr(line))
        except:
            pass

# Start reading the SSE stream in a background thread to keep it alive and consume messages
t = threading.Thread(target=read_sse, args=(resp,))
t.daemon = True
t.start()

import time
time.sleep(1)

# 2. Call tools/list
list_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}
req2 = urllib.request.Request(url, data=json.dumps(list_payload).encode('utf-8'), method='POST')
req2.add_header('Content-Type', 'application/json')
req2.add_header('Accept', 'application/json, text/event-stream')
req2.add_header('mcp-session-id', session_id)

try:
    resp2 = urllib.request.urlopen(req2, context=ctx)
    print("Tools/list POST response:", resp2.read().decode())
except Exception as e:
    print("Error calling tools/list:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())

time.sleep(2)

# 3. Call search_docs for Tripletex
search_payload = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "search_docs",
        "arguments": {"query": "NorgesGruppen"}
    }
}
req3 = urllib.request.Request(url, data=json.dumps(search_payload).encode('utf-8'), method='POST')
req3.add_header('Content-Type', 'application/json')
req3.add_header('Accept', 'application/json, text/event-stream')
req3.add_header('mcp-session-id', session_id)

try:
    resp3 = urllib.request.urlopen(req3, context=ctx)
    print("search_docs POST response:", resp3.read().decode())
except Exception as e:
    print("Error calling search_docs:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())

time.sleep(3)
