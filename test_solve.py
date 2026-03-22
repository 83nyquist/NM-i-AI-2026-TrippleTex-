import requests

url = "http://localhost:8000/solve"
payload = {
    "prompt": "Create a new project named 'AI Sandbox Project'.",
    "tripletex_credentials": {
        "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
        "session_token": "eyJ0b2tlbklkIjoyMTQ3NjkxMzM1LCJ0b2tlbiI6IjA1Zjc3ZGQwLTdjYmUtNGE5MC04ZDQ4LTYyZWVlOWEwNzBlYiJ9"
    }
}

response = requests.post(url, json=payload)
print(response.status_code)
print(response.text)