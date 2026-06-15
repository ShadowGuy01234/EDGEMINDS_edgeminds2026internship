import sqlite3
import json
import math
from typing import List, Dict, Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def calculate_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Calculates cosine similarity between two float vectors.
    """
    if HAS_NUMPY:
        arr1 = np.array(v1)
        arr2 = np.array(v2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(arr1, arr2) / (norm1 * norm2))
    else:
        dot_product = sum(x * y for x, y in zip(v1, v2))
        mag1 = math.sqrt(sum(x * x for x in v1))
        mag2 = math.sqrt(sum(x * x for x in v2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot_product / (mag1 * mag2)

def vector_search(conn: sqlite3.Connection, embedder, keywords: List[str], top_k: int = 10, has_vss: bool = False) -> List[Dict[str, Any]]:
    """
    Searches the vector store for symbols matching the query keywords.
    If sqlite-vss is available, performs search in SQL. Otherwise, uses Python fallback.
    Returns: list of { name, file_path, kind, similarity } sorted by similarity descending.
    """
    if not keywords:
        return []
        
    query_str = " ".join(keywords)
    query_vector = embedder.embed(query_str)
    
    results: List[Dict[str, Any]] = []
    
    if has_vss:
        try:
            cursor = conn.cursor()
            # Perform query on symbol_vectors virtual table
            # sqlite-vss returns 'distance' (cosine distance)
            query_vector_json = json.dumps(query_vector)
            cursor.execute(
                """
                SELECT rowid, distance FROM symbol_vectors 
                WHERE vss_search(embedding, ?) 
                LIMIT ?
                """,
                (query_vector_json, top_k * 2) # Get extra to join and filter
            )
            rows = cursor.fetchall()
            
            # Join rowids back to symbols table
            for rowid, distance in rows:
                cursor.execute(
                    "SELECT name, file_path, kind FROM symbols WHERE id = ?",
                    (rowid,)
                )
                sym_row = cursor.fetchone()
                if sym_row:
                    similarity = 1.0 - distance
                    if similarity >= 0.35:
                        results.append({
                            "name": sym_row[0],
                            "file_path": sym_row[1],
                            "kind": sym_row[2],
                            "similarity": round(similarity, 4)
                        })
            # Sort and truncate to top_k
            results = sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_k]
            return results
        except sqlite3.OperationalError:
            # Fallback to python search if virtual table search fails for any reason
            pass
            
    # Python Fallback Search
    cursor = conn.cursor()
    cursor.execute("SELECT name, file_path, kind, embedding FROM symbols")
    rows = cursor.fetchall()
    
    for name, file_path, kind, embedding_json in rows:
        if not embedding_json:
            continue
        try:
            sym_vector = json.loads(embedding_json)
            similarity = calculate_cosine_similarity(query_vector, sym_vector)
            if similarity >= 0.35:
                results.append({
                    "name": name,
                    "file_path": file_path,
                    "kind": kind,
                    "similarity": round(similarity, 4)
                })
        except Exception:
            continue
            
    # Sort by similarity and slice top_k
    results = sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_k]
    return results
