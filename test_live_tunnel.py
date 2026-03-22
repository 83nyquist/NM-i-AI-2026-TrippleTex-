import requests
import json
import time

try:
    with open("serveo_url.txt", "r") as f:
        url = f.read().strip()
except FileNotFoundError:
    print("serveo_url.txt not found. Is the tunnel running?")
    exit(1)

solve_url = f"{url}/solve"

payload = {
    "prompt": "List the customer named 'AI Sandbox Test Corp', and update its email to 'test@aisandbox.com'. Check your work.",
    "tripletex_credentials": {
        "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
        "session_token": "eyJ0b2tlbklkIjoyMTQ3NjkxMzM1LCJ0b2tlbiI6IjA1Zjc3ZGQwLTdjYmUtNGE5MC04ZDQ4LTYyZWVlOWEwNzBlYiJ9"
    }
}

print(f"Sending live task to {solve_url}...")
start_time = time.time()

try:
    # 5 minute timeout since Serveo does not drop us early
    response = requests.post(solve_url, json=payload, timeout=300)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
except Exception as e:
    print(f"Request failed: {e}")
