import time
import sqlite3
from typing import Dict, Any, List

from router.fallback import RouterDecision
from indexer.graph_query import graph_trace
from indexer.vector_query import vector_search
from indexer.db import HAS_VSS

def execute(conn: sqlite3.Connection, embedder, decision: RouterDecision) -> Dict[str, Any]:
    """
    Orchestrates index searches based on the routing decision.
    Executes the appropriate graph and/or vector queries and returns a unified TraceResult.
    """
    start_time = time.time()
    
    # Check if database has sqlite-vss loaded
    has_vss = HAS_VSS
    
    tool_used = decision.tool
    keywords = decision.keywords
    
    seed = None
    symbol_matches: List[Dict[str, Any]] = []
    dependents: List[Dict[str, Any]] = []
    dependencies: List[Dict[str, Any]] = []
    depth_capped = False
    no_match = False
    
    # 1. Vector Search Path
    if tool_used in ("vector", "hybrid"):
        # Fetch top 10 matches
        matches = vector_search(conn, embedder, keywords, top_k=10, has_vss=has_vss)
        symbol_matches = matches
        
        if not matches:
            no_match = True
        else:
            # Anchor seed on the top match
            top = matches[0]
            # Find kind for seed mapping
            seed = {
                "file_path": top["file_path"],
                "symbol": top["name"],
                "kind": top["kind"],
                "similarity": top["similarity"]
            }
            
    # 2. Graph Traversal Path
    if tool_used == "graph":
        # We need a seed file to run BFS. Find the single top symbol match
        matches = vector_search(conn, embedder, keywords, top_k=1, has_vss=has_vss)
        if not matches:
            no_match = True
        else:
            top = matches[0]
            seed = {
                "file_path": top["file_path"],
                "symbol": top["name"],
                "kind": top["kind"],
                "similarity": top["similarity"]
            }
            
    # Run BFS trace if we have a seed file and need graph details
    if seed and tool_used in ("graph", "hybrid") and not no_match:
        trace_res = graph_trace(conn, seed["file_path"], depth=3)
        dependents = trace_res.get("dependents", [])
        dependencies = trace_res.get("dependencies", [])
        depth_capped = trace_res.get("depth_capped", False)
        
    execution_ms = int((time.time() - start_time) * 1000)
    
    # Construct the canonical TraceResult payload
    return {
        "query": decision.slm_raw, # We can override this at the API level with user query
        "routed_by": decision.routed_by,
        "tool_used": tool_used,
        "keywords": keywords,
        "slm_latency_ms": decision.latency_ms,
        "seed": seed,
        "symbol_matches": symbol_matches if tool_used in ("vector", "hybrid") else [],
        "dependents": dependents,
        "dependencies": dependencies,
        "depth_capped": depth_capped,
        "no_match": no_match,
        "execution_ms": execution_ms
    }
