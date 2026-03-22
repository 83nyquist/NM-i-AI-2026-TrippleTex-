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

session_id = None
try:
    resp = urllib.request.urlopen(req, context=ctx)
    session_id = resp.getheader('mcp-session-id')
except Exception as e:
    sys.exit(1)

def read_sse(resp):
    try:
        for line in resp: pass
    except: pass

t = threading.Thread(target=read_sse, args=(resp,))
t.daemon = True
t.start()

time.sleep(1)

def search_docs(query, req_id):
    search_payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {
            "name": "search_docs",
            "arguments": {"query": query}
        }
    }
    req3 = urllib.request.Request(url, data=json.dumps(search_payload).encode('utf-8'), method='POST')
    req3.add_header('Content-Type', 'application/json')
    req3.add_header('Accept', 'application/json, text/event-stream')
    if session_id:
        req3.add_header('mcp-session-id', session_id)
    try:
        resp3 = urllib.request.urlopen(req3, context=ctx)
        print(f"--- RESULTS FOR {query} ---")
        print(resp3.read().decode())
    except Exception as e:
        print(f"Search error for {query}:", e)
    time.sleep(1)

search_docs("Authorization: Bearer", 2)
search_docs("we send it as a Bearer token", 3)
search_docs("API key when submitting", 4)
