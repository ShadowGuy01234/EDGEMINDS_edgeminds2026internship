import functools
import time
from typing import Dict, Any

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


@functools.lru_cache(maxsize=256)
def _compute_route(query: str) -> RouterDecision:
    """
    Pure, deterministic routing — no network call.
    LRU-cached so repeated/identical queries are free.
    Cache key is the raw query string (case-preserved).
    """
    start_time = time.time()
    tool = classify_query_rules(query)
    fallback = fallback_route(query)
    latency_ms = int((time.time() - start_time) * 1000)
    return RouterDecision(
        tool=tool,
        keywords=fallback.keywords,
        routed_by="rules",
        slm_raw="",
        latency_ms=latency_ms
    )


def call_ollama(query: str) -> RouterDecision:
    """
    Routes the query using deterministic keyword rules + regex extraction.
    Results are LRU-cached (maxsize=256) so identical queries within a
    session are returned instantly without any recomputation.

    Previously made a blocking HTTP call to Ollama for routing, which added
    2-5 s per query on the Jetson. That call has been removed because:
    - classify_query_rules() already deterministically picks graph/vector/hybrid
    - The LLM's only value was keyword extraction, but those were validated
      against the raw query string anyway, giving no semantic advantage
    - fallback_route() reliably extracts the same keywords via regex
    """
    return _compute_route(query)
