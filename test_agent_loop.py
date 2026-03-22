import os
import json
import logging
from google import genai
from agent import run_agent

logging.basicConfig(level=logging.INFO)

def test_agent():
    # Load API key
    try:
        with open("/home/devstar18111/nmai/config/config.json", "r") as f:
            config = json.load(f)
            api_key = config.get("apiKey")
    except Exception as e:
        print(f"Could not load API key: {e}")
        return
        
    client = genai.Client(api_key=api_key)
    
    prompt = "Create a new customer named 'AI Sandbox Test Corp'. Make sure you use the right endpoints and check if it was created successfully."
    
    print("Running agent...")
    res = run_agent(
        client=client,
        base_url="https://kkpqfuj-amager.tripletex.dev/v2",
        session_token="eyJ0b2tlbklkIjoyMTQ3NjkxMzM1LCJ0b2tlbiI6IjA1Zjc3ZGQwLTdjYmUtNGE5MC04ZDQ4LTYyZWVlOWEwNzBlYiJ9",
        prompt=prompt
    )
    print("Final Agent Response:")
    print(res)

if __name__ == "__main__":
    test_agent()
