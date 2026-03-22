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

queries = ["API key", "optional API key", "authentication", "submit"]

for i, query in enumerate(queries):
    # Initialize new session for each query to be safe
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
    
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        session_id = resp.getheader('mcp-session-id')
    except Exception as e:
        print("Init error:", e)
        continue

    def read_sse(resp):
        try:
            for line in resp: pass
        except: pass

    t = threading.Thread(target=read_sse, args=(resp,))
    t.daemon = True
    t.start()
    time.sleep(0.5)

    tool_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_docs",
            "arguments": {
                "query": query
            }
        }
    }
    req2 = urllib.request.Request(url, data=json.dumps(tool_payload).encode('utf-8'), method='POST')
    req2.add_header('Content-Type', 'application/json')
    req2.add_header('Accept', 'application/json, text/event-stream')
    req2.add_header('mcp-session-id', session_id)

    try:
        resp2 = urllib.request.urlopen(req2, context=ctx)
        print(f"--- RESULTS FOR: {query} ---")
        print(resp2.read().decode())
    except Exception as e:
        print(f"Error querying {query}:", e)
        if hasattr(e, 'read'):
            print(e.read().decode())
    time.sleep(0.5)
