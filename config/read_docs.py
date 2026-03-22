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

# Initialize
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
resp = urllib.request.urlopen(req, context=ctx)
session_id = resp.getheader('mcp-session-id')

def read_sse(resp):
    for line in resp:
        pass

t = threading.Thread(target=read_sse, args=(resp,))
t.daemon = True
t.start()
time.sleep(1)

uris = [
    "challenge://norgesgruppen-data/overview",
    "challenge://norgesgruppen-data/submission",
    "challenge://norgesgruppen-data/examples",
    "challenge://norgesgruppen-data/scoring"
]

for i, uri in enumerate(uris):
    read_payload = {
        "jsonrpc": "2.0",
        "id": i+2,
        "method": "resources/read",
        "params": {
            "uri": uri
        }
    }
    req2 = urllib.request.Request(url, data=json.dumps(read_payload).encode('utf-8'), method='POST')
    req2.add_header('Content-Type', 'application/json')
    req2.add_header('Accept', 'application/json, text/event-stream')
    req2.add_header('mcp-session-id', session_id)

    try:
        resp2 = urllib.request.urlopen(req2, context=ctx)
        print(f"--- {uri} ---")
        print(resp2.read().decode())
    except Exception as e:
        print(f"Error reading {uri}:", e)
        if hasattr(e, 'read'):
            print(e.read().decode())
    time.sleep(1)

