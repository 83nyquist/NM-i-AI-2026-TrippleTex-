import json
import logging
import httpx
from google import genai
from agent import run_agent

# Monkey patch httpx to print the body
original_post = httpx.post
def mock_post(*args, **kwargs):
    print("MOCKED POST URL:", args[0] if args else kwargs.get("url"))
    print("MOCKED POST JSON:", json.dumps(kwargs.get("json"), indent=2))
    return original_post(*args, **kwargs)
httpx.post = mock_post

logging.basicConfig(level=logging.INFO)

try:
    with open("/home/devstar18111/nmai/config/config.json", "r") as f:
        api_key = json.load(f).get("apiKey")
except:
    exit(1)

client = genai.Client(api_key=api_key)
prompt = "Create a new employee. First name: Jane, Last name: Doe. Email: jane.doe@example.com. Assign them the Administrator role."
base_url = "https://kkpqfuj-amager.tripletex.dev/v2"
session_token = "eyJ0b2tlbklkIjoyMTQ3NjkxMzM1LCJ0b2tlbiI6IjA1Zjc3ZGQwLTdjYmUtNGE5MC04ZDQ4LTYyZWVlOWEwNzBlYiJ9"

run_agent(client=client, base_url=base_url, session_token=session_token, prompt=prompt)
