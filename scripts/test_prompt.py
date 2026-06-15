import httpx
import json
from api.config import OLLAMA_BASE_URL, OLLAMA_MODEL

# We will try a tuned prompt
SYSTEM_PROMPT = """You are a code navigation router. Your only job is to output a JSON routing decision.

Rules:
- Output ONLY a JSON object. No explanation. No preamble. No markdown.
- "tool" must be exactly one of: "graph", "vector", "hybrid"
- "keywords" must be an array of 2 to 5 strings from the user's query
- Use "graph" ONLY for imports, dependency queries, or file-to-file relationships
- Use "vector" ONLY to find a specific function, class, symbol, or search term
- Use "hybrid" for impact analysis ("what breaks"), code changes, or when unsure

Output format:
{"tool": "...", "keywords": ["...", "..."]}"""

test_cases = [
    # Spec queries
    ("What files import the auth module?", "graph", "auth"),
    ("Find the JWT decode function", "vector", "jwt"),
    ("Where is rate limiting handled and what depends on it?", "hybrid", "rate"),
    ("Show me the database connection module", "vector", "database"),
    ("What breaks if I change the middleware?", "hybrid", "middleware"),
    
    # Custom queries
    ("Find the class UserProfile in user routes", "vector", "user"),
    ("What imports session.py in the database directory?", "graph", "session"),
    ("Where is verification code generated?", "vector", "verification"),
    ("Who depends on config module?", "graph", "config"),
    ("Find API key authentication middleware", "vector", "auth"),
    ("Which files depend on helper.py?", "graph", "helper"),
    ("Find the get_status function inside status.py", "vector", "status"),
    ("Where is jwt_middleware and who uses it?", "hybrid", "jwt"),
    ("What dependencies does database session have?", "graph", "database"),
    ("Locate the class AuthMiddleware", "vector", "auth"),
    ("Is there a custom exception handler for API errors?", "vector", "exception"),
    ("Show dependencies of user.py", "graph", "user"),
    ("List files importing main.py", "graph", "main"),
    ("What depends on the email handler and where is it located?", "hybrid", "email"),
    ("Where does the router get initialized?", "vector", "router")
]

def test():
    passed = 0
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    
    for query, expected_tool, expected_kw in test_cases:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Query: {query}"}
            ],
            "format": "json",
            "options": {
                "temperature": 0.0,
                "num_predict": 80,
                "num_ctx": 512,
                "stop": ["\n\n", "```", "\n}"]
            },
            "stream": False
        }
        try:
            resp = httpx.post(url, json=payload, timeout=5.0)
            content = resp.json()["message"]["content"].strip()
            # clean markdown
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            decision = json.loads(content.strip())
            tool = decision.get("tool")
            is_pass = (tool == expected_tool)
            if is_pass:
                passed += 1
            print(f"Query: '{query}' | Expected: {expected_tool} | Got: {tool} | {'PASS' if is_pass else 'FAIL'}")
        except Exception as e:
            print(f"Query: '{query}' | Error: {e} | FAIL")
            
    print(f"Total passed: {passed}/{len(test_cases)} ({passed/len(test_cases)*100:.1f}%)")

if __name__ == "__main__":
    test()
