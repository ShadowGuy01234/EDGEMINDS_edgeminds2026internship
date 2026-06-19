import time
import sqlite3
import os
import re
from typing import Dict, Any, List, Optional

from router.fallback import RouterDecision
from indexer.graph_query import graph_trace
from indexer.vector_query import vector_search
from indexer.db import HAS_VSS

def find_seed_file_by_name(conn: sqlite3.Connection, query: str, keywords: List[str]) -> Optional[str]:
    """
    Checks if the query or keywords contain a file name or path that exists in the nodes table.
    Returns the file_path if found, otherwise None.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM nodes")
        file_paths = [row[0] for row in cursor.fetchall()]
        
        query_lower = query.lower().replace('\\', '/')
        query_normalized = query_lower.replace(' ', '_').replace('-', '_')
        
        # Sort paths by length descending so that longer paths match first
        for path in sorted(file_paths, key=len, reverse=True):
            path_clean = path.lower().replace('\\', '/')
            basename = os.path.basename(path_clean)
            
            # If the exact basename is in the query (e.g. "config.py")
            if basename in query_lower:
                return path
                
            # If name without extension matches (e.g. "config")
            name_no_ext = os.path.splitext(basename)[0]
            if len(name_no_ext) > 3:
                # Check normalized query (for "file scanner" -> "file_scanner" matches)
                if name_no_ext in query_normalized:
                    return path
                # Word boundary check
                pattern = r'\b' + re.escape(name_no_ext) + r'\b'
                if re.search(pattern, query_lower):
                    return path
                    
        # Check keywords directly
        for path in file_paths:
            path_clean = path.lower().replace('\\', '/')
            basename = os.path.basename(path_clean)
            name_no_ext = os.path.splitext(basename)[0]
            for kw in keywords:
                kw_clean = kw.lower().strip()
                if kw_clean == basename or (len(name_no_ext) > 3 and kw_clean == name_no_ext):
                    return path
    except Exception:
        pass
    return None

def execute(conn: sqlite3.Connection, embedder, decision: RouterDecision, layer_filter: str = None) -> Dict[str, Any]:
    """
    Orchestrates index searches based on the routing decision.
    Executes the appropriate graph and/or vector queries and returns a unified TraceResult.
    """
    start_time = time.time()
    
    # Check if database has sqlite-vss loaded
    has_vss = HAS_VSS
    
    tool_used = decision.tool
    keywords = decision.keywords
    
    # In api.main.py we can set decision.slm_raw, but if it is empty, default to query text
    query_text = decision.slm_raw if decision.slm_raw else " ".join(keywords)
    
    seed = None
    symbol_matches: List[Dict[str, Any]] = []
    dependents: List[Dict[str, Any]] = []
    dependencies: List[Dict[str, Any]] = []
    depth_capped = False
    no_match = False
    
    # 1. Vector Search Path
    if tool_used in ("vector", "hybrid"):
        # Fetch top 10 matches
        matches = vector_search(conn, embedder, keywords, top_k=10, has_vss=has_vss, layer_filter=layer_filter)
        symbol_matches = matches
        
        if not matches:
            # Check if we can still find a direct file path match
            matched_file = find_seed_file_by_name(conn, query_text, keywords)
            if matched_file:
                top = {
                    "file_path": matched_file,
                    "name": os.path.basename(matched_file),
                    "kind": "file",
                    "layer": "unknown",
                    "similarity": 1.0
                }
                seed = {
                    "file_path": top["file_path"],
                    "symbol": top["name"],
                    "kind": top["kind"],
                    "layer": top.get("layer", "unknown"),
                    "similarity": top["similarity"]
                }
            else:
                no_match = True
        else:
            # Check if there is a direct file path match in the query
            matched_file = find_seed_file_by_name(conn, query_text, keywords)
            if matched_file:
                file_matches = [m for m in matches if m["file_path"] == matched_file]
                if file_matches:
                    top = file_matches[0]
                else:
                    top = {
                        "file_path": matched_file,
                        "name": os.path.basename(matched_file),
                        "kind": "file",
                        "layer": "unknown",
                        "similarity": 1.0
                    }
            else:
                # Prioritize non-test files for the seed
                non_test_matches = [m for m in matches if m.get("layer") != "test"]
                top = non_test_matches[0] if non_test_matches else matches[0]
                
            seed = {
                "file_path": top["file_path"],
                "symbol": top["name"],
                "kind": top["kind"],
                "layer": top.get("layer", "unknown"),
                "similarity": top["similarity"]
            }
            
    # 2. Graph Traversal Path
    if tool_used == "graph":
        # Check if there is a direct file path match in the query
        matched_file = find_seed_file_by_name(conn, query_text, keywords)
        if matched_file:
            seed = {
                "file_path": matched_file,
                "symbol": os.path.basename(matched_file),
                "kind": "file",
                "layer": "unknown",
                "similarity": 1.0
            }
        else:
            # We need a seed file to run BFS. Find the single top symbol match
            matches = vector_search(conn, embedder, keywords, top_k=5, has_vss=has_vss, layer_filter=layer_filter)
            if not matches:
                no_match = True
            else:
                # Prioritize non-test files
                non_test_matches = [m for m in matches if m.get("layer") != "test"]
                top = non_test_matches[0] if non_test_matches else matches[0]
                seed = {
                    "file_path": top["file_path"],
                    "symbol": top["name"],
                    "kind": top["kind"],
                    "layer": top.get("layer", "unknown"),
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
        "query": query_text,
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
