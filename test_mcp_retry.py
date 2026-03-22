import logging
from mcp_client import MCPClient
import time

logging.basicConfig(level=logging.INFO)

def main():
    print("Initializing MCPClient (which includes 15 retries)...")
    start_time = time.time()
    mcp = MCPClient()
    
    if mcp.session_id:
        print(f"Successfully connected! Session ID: {mcp.session_id}")
    else:
        print("Failed to connect after all retries.")
        return
        
    print("Testing search_docs tool (which also includes retries)...")
    res = mcp.call_tool("search_docs", {"query": "employee"})
    print("Response received:")
    
    # Just print the first 500 chars to avoid huge output
    res_str = str(res)
    print(res_str[:500] + ("..." if len(res_str) > 500 else ""))
    
    print(f"Total time elapsed: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
