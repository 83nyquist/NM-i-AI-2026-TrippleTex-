import subprocess
import time
import re
import requests
import sys

print("Starting FastAPI server...", flush=True)
server_process = subprocess.Popen(["uvicorn", "main:app", "--port", "8000"])

time.sleep(3)
print("Starting localhost.run tunnel...", flush=True)

ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:8000", "nokey@localhost.run"]
tunnel_process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

url = None
for _ in range(50):
    line = tunnel_process.stdout.readline()
    if not line:
        break
    print("Tunnel:", line.strip(), flush=True)
    # 28bd2812f20a59.lhr.life tunneled with tls termination, https://28bd2812f20a59.lhr.life
    match = re.search(r'(https://[a-zA-Z0-9-]+\.lhr\.life)', line)
    if match:
        url = match.group(1)
        break

if url:
    with open("serveo_url.txt", "w") as f:
        f.write(url)
    
    print("\n" + "="*60, flush=True)
    print(f"SUCCESS! Your agent is live at: {url}", flush=True)
    print(f"Submit THIS endpoint to Tripletex: {url}/solve", flush=True)
    print("="*60 + "\n", flush=True)
    
    # Optional testing
    try:
        health_check = requests.get(f"{url}/health", timeout=10)
        print(f"Health check status: {health_check.status_code} - {health_check.text}", flush=True)
    except Exception as e:
        print(f"Health check failed: {e}", flush=True)
        
    try:
        tunnel_process.wait()
    except KeyboardInterrupt:
        print("Stopping tunnel...", flush=True)
        tunnel_process.kill()
        server_process.kill()
else:
    print("Failed to get a URL from localhost.run.", flush=True)
    tunnel_process.kill()
    server_process.kill()
    sys.exit(1)
