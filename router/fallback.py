import re
import os
import time
from dataclasses import dataclass
from typing import List

# Stopwords to filter out during fallback keyword extraction
STOPWORDS = {
    "where", "does", "what", "how", "is", "the", "a", "an", "in",
    "of", "to", "my", "our", "it", "if", "i", "change", "find",
    "show", "me", "and", "or", "which", "who", "when", "that",
    "about", "your", "codebase", "project", "repo", "repository",
    "function", "class", "symbol", "module", "file", "directory",
    "folder", "method", "variable", "code", "object", "component",
    "handler", "service", "route", "package"
}

@dataclass
class RouterDecision:
    tool: str           # "graph" | "vector" | "hybrid"
    keywords: List[str]
    routed_by: str      # "slm" | "fallback"
    slm_raw: str        # raw model output for debugging
    latency_ms: int     # latency in milliseconds

def fallback_route(query: str, slm_raw: str = "", latency_ms: int = 0) -> RouterDecision:
    """
    Standard fallback routing that parses the query using regex/stopwords when the SLM fails.
    """
    # Standardize string: lowercase and remove punctuation
    clean_query = re.sub(r"[^\w\s-]", "", query.lower())
    tokens = clean_query.split()
    
    # Extract keywords
    keywords = [t for t in tokens if t not in STOPWORDS]
    # Deduplicate while preserving order
    seen = set()
    deduped_keywords = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            deduped_keywords.append(k)
            
    # Cap at 5 keywords
    final_keywords = deduped_keywords[:5]
    
    # Ensure logs folder exists and log the fallback trigger
    os.makedirs("logs", exist_ok=True)
    with open("logs/router_fallback.log", "a", encoding="utf-8") as f:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        f.write(f"[{timestamp}] Query: '{query}' | SLM Output: '{slm_raw}' | Fallback Keywords: {final_keywords}\n")
        
    return RouterDecision(
        tool="hybrid",
        keywords=final_keywords,
        routed_by="fallback",
        slm_raw=slm_raw,
        latency_ms=latency_ms
    )
