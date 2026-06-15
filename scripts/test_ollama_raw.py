import httpx
from router.prompt import SYSTEM_PROMPT, build_user_turn
from api.config import OLLAMA_BASE_URL, OLLAMA_MODEL

def test():
    query = "Find the JWT decode function"
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_turn(query)}
        ],
        "options": {
            "temperature": 0.0,
            "num_predict": 80,
            "num_ctx": 512,
            "stop": ["\n\n", "```", "\n}"]
        },
        "stream": False
    }
    
    print(f"Query: '{query}'")
    try:
        resp = httpx.post(url, json=payload, timeout=10.0)
        print("Response status:", resp.status_code)
        print("Raw content:")
        print(resp.json()["message"]["content"])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
