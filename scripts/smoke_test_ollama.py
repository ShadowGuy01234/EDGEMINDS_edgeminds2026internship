import httpx
import json
import sys

import os

# Try to load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    url = f"{base_url.rstrip('/')}/api/generate"
    
    payload = {
        "model": model,
        "prompt": "Respond with the word test.",
        "stream": False,
        "options": {
            "num_ctx": 1024,
            "num_gpu": 1,
            "use_mmap": True
        }
    }
    
    print(f"Connecting to Ollama at {url}...")
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Response content:")
            print(json.dumps(data, indent=2))
            print("\nOllama smoke test PASSED!")
            sys.exit(0)
        else:
            print(f"Failed with status: {response.status_code}")
            print(response.text)
            sys.exit(1)
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
