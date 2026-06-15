import httpx
import json
import sys

def main():
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.2:1b",
        "prompt": "Respond with the word test.",
        "stream": False
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
