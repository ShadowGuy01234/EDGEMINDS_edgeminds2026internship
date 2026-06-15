import json
import sqlite3
import sys

from api.config import DB_PATH
from indexer import embedder
from router.slm_router import call_ollama
from engine.executor import execute

def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Find the file scanner and what files import it"
    print(f"User Query: '{query}'")
    
    # Establish connection
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Route the query using the SLM router
    print("Calling SLM Router...")
    decision = call_ollama(query)
    print(f"Decision: tool='{decision.tool}', keywords={decision.keywords}, routed_by='{decision.routed_by}' ({decision.latency_ms}ms)")
    
    # 2. Execute search using execution engine
    print("Executing query search...")
    trace_result = execute(conn, embedder, decision)
    # Inject correct query text
    trace_result["query"] = query
    
    # 3. Print result
    print("\n=== Pipeline TraceResult Output ===")
    print(json.dumps(trace_result, indent=2))
    print("===================================\n")
    
    conn.close()

if __name__ == "__main__":
    main()
