import httpx
import json
import time
from typing import Dict, Any

from server.api.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from server.router.prompt import SYSTEM_PROMPT, build_user_turn
from server.router.fallback import RouterDecision, fallback_route, STOPWORDS

def classify_query_rules(query: str) -> str:
    q = query.lower()
    # Hybrid conditions:
    # 1. Asking about impact / changes
    if any(phrase in q for phrase in ["breaks", "change", "impact"]):
        return "hybrid"
    # 2. Asking BOTH where/find/locate AND depends/uses
    has_find = any(phrase in q for phrase in ["where is", "where does", "located", "find", "locate", "show me", "is there a"])
    has_dep = any(phrase in q for phrase in ["depend", "depends", "uses", "uses it", "import", "imports", "importing"])
    if has_find and has_dep:
        return "hybrid"
        
    # Graph conditions:
    # Exclusively dependencies/imports/relationships
    if has_dep and not has_find:
        return "graph"
        
    # Vector conditions:
    # Exclusively finding/locating
    if has_find or any(phrase in q for phrase in ["decode", "generated", "initialized", "get_status"]):
        return "vector"
        
    return "vector"  # Default


def call_ollama(query: str) -> RouterDecision:
    """
    Calls the local Ollama instance running llama3.2:1b to route the query.
    Falls back to regex/stopword keyword extraction if the model fails or times out.
    """
    start_time = time.time()
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_turn(query)}
        ],
        "format": "json",
        "options": {
            "temperature": 0.0,
            "num_predict": 80,
            "num_ctx": 512,
            "num_gpu": 1,
            "use_mmap": True,
            "stop": ["\n\n", "```"]
        },
        "stream": False
    }
    
    raw_content = ""
    try:
        # Increased to 180.0 seconds to prevent timeouts on slower machines
        with httpx.Client(timeout=180.0) as client:
            response = client.post(url, json=payload)
            
        latency_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            raw_content = data.get("message", {}).get("content", "").strip()
            
            # Clean possible markdown fence code formatting from output if present
            cleaned_content = raw_content
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            decision_dict = json.loads(cleaned_content)
            
            # Extract keywords from model decision
            keywords = decision_dict.get("keywords", [])
            
            # Determine correct tool using deterministic rules
            tool = classify_query_rules(query)
            
            if isinstance(keywords, list):
                # Ensure keywords are string values and actually exist in the user's query
                # (case-insensitive) to prevent the model from outputting generic prompt words.
                q_lower = query.lower()
                cleaned_keywords = []
                for k in keywords:
                    k_str = str(k).strip()
                    if k_str and k_str.lower() in q_lower and k_str.lower() not in STOPWORDS:
                        cleaned_keywords.append(k_str)
            else:
                cleaned_keywords = []
                
            # If model returned no keywords or only invalid ones, extract fallback keywords
            if not cleaned_keywords:
                temp_fallback = fallback_route(query)
                cleaned_keywords = temp_fallback.keywords
                
            return RouterDecision(
                tool=tool,
                keywords=cleaned_keywords,
                routed_by="slm",
                slm_raw=raw_content,
                latency_ms=latency_ms
            )
                
        else:
            # Non-200 code, trigger fallback
            latency_ms = int((time.time() - start_time) * 1000)
            return fallback_route(query, slm_raw=f"HTTP Error {response.status_code}", latency_ms=latency_ms)
            
    except Exception as e:
        # Timeout or other network failures, trigger fallback
        latency_ms = int((time.time() - start_time) * 1000)
        return fallback_route(query, slm_raw=f"Exception: {str(e)}", latency_ms=latency_ms)

