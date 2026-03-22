import requests
import json
import threading
import time
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, sse_url="https://mcp-docs.ainm.no/mcp"):
        self.sse_url = sse_url
        self.session_id = None
        self.msg_id = 1
        self._connect()

    def _connect(self):
        init_payload = {
            "jsonrpc": "2.0", 
            "id": 1, 
            "method": "initialize", 
            "params": {
                "protocolVersion": "2024-11-05", 
                "capabilities": {}, 
                "clientInfo": { "name": "python-agent", "version": "1.0.0" }
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        for attempt in range(3):
            try:
                resp = requests.post(self.sse_url, json=init_payload, headers=headers, stream=True, timeout=10)
                self.session_id = resp.headers.get("mcp-session-id")
                
                if not self.session_id:
                    logger.error(f"Failed to connect (attempt {attempt+1}): Missing mcp-session-id")
                    time.sleep(1)
                    continue
                    
                logger.info(f"Connected to MCP SSE. Session ID: {self.session_id}")
                
                # Start background thread to keep connection alive
                t = threading.Thread(target=self._read_sse, args=(resp,))
                t.daemon = True
                t.start()
                
                # Allow time for the connection to fully establish
                time.sleep(1)
                
                # Send initialized notification
                init_notif = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                self._post(init_notif, is_init=True)
                return
                
            except Exception as e:
                logger.error(f"Failed to connect to MCP (attempt {attempt+1}): {e}")
                time.sleep(1)
        logger.error("Failed to connect to MCP after all retries.")

    def _read_sse(self, resp):
        try:
            for line in resp.iter_lines():
                if line:
                    logger.debug(f"SSE line received: {len(line)}")
        except Exception as e:
            logger.error(f"SSE thread exception: {e}")

    def _post(self, payload, is_init=False):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
            
        for attempt in range(3):
            try:
                resp = requests.post(self.sse_url, json=payload, headers=headers, timeout=10)
                
                if resp.status_code >= 400:
                    logger.error(f"MCP POST error (attempt {attempt+1}): HTTP {resp.status_code} {resp.text}")
                    if "Session not found" in resp.text or resp.status_code == 404:
                        if not is_init:
                            logger.warning("Session not found, attempting to reconnect...")
                            self._connect()
                            if self.session_id:
                                headers["mcp-session-id"] = self.session_id
                    time.sleep(1)
                    continue
                    
                # The server might respond with a regular JSON or an SSE payload containing JSON
                text = resp.text
                for line in text.splitlines():
                    if line.startswith('data: '):
                        return json.loads(line[6:])
                
                if text:
                    return json.loads(text)
                return {}
            except Exception as e:
                logger.error(f"MCP POST exception (attempt {attempt+1}): {e}")
                time.sleep(1)
        return {"error": "Failed after all retries"}

    def call_tool(self, name, arguments):
        self.msg_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        return self._post(payload)

    def read_resource(self, uri):
        self.msg_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        }
        return self._post(payload)