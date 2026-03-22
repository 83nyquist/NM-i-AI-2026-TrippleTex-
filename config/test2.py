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

# GET request to establish SSE and get endpoint
req = urllib.request.Request(url, method='GET')
req.add_header('Accept', 'text/event-stream')

session_id = None
post_endpoint = None

try:
    resp = urllib.request.urlopen(req, context=ctx)
    session_id = resp.getheader('mcp-session-id')
    print("Got session ID:", session_id)
except Exception as e:
    print("Error connecting to SSE:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())
    sys.exit(1)

def read_sse(resp):
    global post_endpoint
    for line in resp:
        try:
            line = line.decode('utf-8').strip()
            if line:
                print("SSE LINE:", line)
            if line.startswith("event: endpoint"):
                # The next line should be data: <uri>
                pass
            elif line.startswith("data: ") and post_endpoint is None:
                # Need to be careful. The endpoint event sends URI in data:
                # Let's just try to parse it if it looks like a URI or endpoint
                pass
        except:
            pass

def read_sse_better(resp):
    global post_endpoint
    is_endpoint_event = False
    for line in resp:
        try:
            line = line.decode('utf-8').strip()
            if not line: continue
            print("SSE LINE:", line)
            if line == "event: endpoint":
                is_endpoint_event = True
            elif line.startswith("data: "):
                data_val = line[6:]
                if is_endpoint_event:
                    post_endpoint = data_val
                    print("GOT POST ENDPOINT:", post_endpoint)
                    is_endpoint_event = False
        except Exception as e:
            print("SSE Parse Error:", e)

t = threading.Thread(target=read_sse_better, args=(resp,))
t.daemon = True
t.start()

time.sleep(2)

if not post_endpoint:
    print("Did not receive post endpoint")
    sys.exit(1)

# Ensure endpoint is absolute
if post_endpoint.startswith("/"):
    post_endpoint = "https://mcp-docs.ainm.no" + post_endpoint

print("Using POST endpoint:", post_endpoint)

# 1. Initialize
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
req1 = urllib.request.Request(post_endpoint, data=json.dumps(init_payload).encode('utf-8'), method='POST')
req1.add_header('Content-Type', 'application/json')
if session_id:
    req1.add_header('mcp-session-id', session_id)

try:
    resp1 = urllib.request.urlopen(req1, context=ctx)
    print("Initialize POST response:", resp1.read().decode())
except Exception as e:
    print("Error calling initialize:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())

time.sleep(1)

# 2. Call search_docs for Tripletex
search_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "search_docs",
        "arguments": {"query": "Tripletex tasks"}
    }
}
req2 = urllib.request.Request(post_endpoint, data=json.dumps(search_payload).encode('utf-8'), method='POST')
req2.add_header('Content-Type', 'application/json')
if session_id:
    req2.add_header('mcp-session-id', session_id)

try:
    resp2 = urllib.request.urlopen(req2, context=ctx)
    print("search_docs POST response:", resp2.read().decode())
except Exception as e:
    print("Error calling search_docs:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())

time.sleep(1)

# Let's search for just Tripletex too
search_payload3 = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "search_docs",
        "arguments": {"query": "Tripletex scenarios"}
    }
}
req3 = urllib.request.Request(post_endpoint, data=json.dumps(search_payload3).encode('utf-8'), method='POST')
req3.add_header('Content-Type', 'application/json')
if session_id:
    req3.add_header('mcp-session-id', session_id)

try:
    resp3 = urllib.request.urlopen(req3, context=ctx)
    print("search_docs POST response:", resp3.read().decode())
except Exception as e:
    pass

time.sleep(3)
