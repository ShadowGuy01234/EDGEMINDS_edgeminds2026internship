import os
import argparse
import json
import time
from typing import Dict, Any, Optional

from server.indexer.db import init_db
from server.indexer.graph_builder import insert_nodes, insert_edges
from server.indexer.vector_builder import insert_symbols
from server.indexer import embedder

def build_index(manifest_path: str, db_path: str, repo_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Main orchestration function to build the SQLite index from the parsed manifest.
    """
    start_time = time.time()
    
    # Standardize paths
    manifest_path = os.path.abspath(manifest_path)
    db_path = os.path.abspath(db_path)
    
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest blueprint file '{manifest_path}' does not exist.")
        
    print(f"Reading manifest blueprints from: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        blueprints = json.load(f)
        
    print(f"Initializing SQLite database at: {db_path}")
    # init_db will connect to the SQLite DB and return the connection
    # It also sets HAS_VSS flag if sqlite-vss loaded successfully
    from server.indexer.db import HAS_VSS
    conn = init_db(db_path)
    has_vss = HAS_VSS
    print(f"SQLite database initialized (sqlite-vss support: {has_vss})")
    
    # 1. Insert Nodes (files)
    print("Inserting workspace files (nodes) into database...")
    insert_nodes(conn, blueprints)
    
    # 2. Insert Edges (import relationships)
    print("Classifying and inserting import links (edges) into database...")
    insert_edges(conn, blueprints)
    
    # 3. Insert Symbols (embeddings for vector search)
    print("Generating symbol embeddings and indexing...")
    
    # Extract repo_path from DB if not provided
    if not repo_path:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'repo_path'")
            row = cursor.fetchone()
            if row:
                repo_path = row[0]
        except Exception:
            pass
            
    insert_symbols(conn, blueprints, embedder, has_vss, repo_path=repo_path)
    
    # Count results
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM nodes")
    node_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*), import_type FROM edges GROUP BY import_type")
    edge_counts = {row[1]: row[0] for row in cursor.fetchall()}
    internal_count = edge_counts.get("internal", 0)
    external_count = edge_counts.get("external", 0)
    
    cursor.execute("SELECT COUNT(*) FROM symbols")
    symbol_count = cursor.fetchone()[0]



    conn.close()
    
    duration_ms = int((time.time() - start_time) * 1000)
    print(f"\nIndex build completed in {duration_ms} ms.")
    print(f"Indexed nodes (files):      {node_count}")
    print(f"Indexed internal imports:    {internal_count}")
    print(f"Indexed external imports:    {external_count}")
    print(f"Indexed symbols:            {symbol_count}")
    
    return {
        "status": "success",
        "nodes_indexed": node_count,
        "internal_edges_indexed": internal_count,
        "external_edges_indexed": external_count,
        "symbols_indexed": symbol_count,
        "duration_ms": duration_ms
    }

def main():
    parser = argparse.ArgumentParser(description="Build database indexes from architectural blueprints.")
    parser.add_argument("--manifest", default="./index/manifest.json", help="Path to parser manifest blueprint file")
    parser.add_argument("--db", default="./index/codegenome.db", help="Path to target SQLite DB file")
    
    args = parser.parse_args()
    build_index(args.manifest, args.db)

if __name__ == "__main__":
    main()
