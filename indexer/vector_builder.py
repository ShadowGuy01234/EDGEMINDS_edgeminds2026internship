import sqlite3
import json
from typing import List, Dict, Any

def insert_symbols(conn: sqlite3.Connection, blueprints: List[Dict[str, Any]], embedder, has_vss: bool):
    """
    Extracts all symbols (functions, classes, exports) from blueprints,
    generates embeddings in batch, and stores them in both symbols and virtual tables.
    """
    cursor = conn.cursor()
    # Clear existing symbols and vector entries
    cursor.execute("DELETE FROM symbols")
    if has_vss:
        try:
            cursor.execute("DELETE FROM symbol_vectors")
        except sqlite3.OperationalError:
            pass
            
    symbols_to_insert = []
    
    for bp in blueprints:
        file_path = bp["file_path"]
        language = bp["language"]
        
        # 1. Functions
        for func in bp.get("functions", []):
            symbols_to_insert.append((file_path, func, "function", language))
            
        # 2. Classes
        for cls in bp.get("classes", []):
            symbols_to_insert.append((file_path, cls, "class", language))
            
        # 3. Exports
        for exp in bp.get("exports", []):
            # Avoid duplicating default exports if they are already named, 
            # but we can insert them as "export" kind
            symbols_to_insert.append((file_path, exp, "export", language))
            
    if not symbols_to_insert:
        return
        
    # Extract unique name strings to embed
    # Wait, if two files have a function with the same name, we can embed it once to be faster,
    # or just batch-embed all of them. Since the list is small, batch-embed is fine.
    names = [item[1] for item in symbols_to_insert]
    
    print(f"Batch embedding {len(names)} symbols...")
    vectors = embedder.embed_batch(names)
    
    # Insert symbols and their corresponding vectors
    for (file_path, name, kind, language), vector in zip(symbols_to_insert, vectors):
        vector_json = json.dumps(vector)
        
        cursor.execute(
            """
            INSERT INTO symbols (file_path, name, kind, language, embedding)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_path, name, kind, language, vector_json)
        )
        symbol_id = cursor.lastrowid
        
        if has_vss:
            try:
                # Convert list of floats to serialized raw bytes/JSON for sqlite-vss
                # E.g. sqlite-vss expects floats as a JSON array string in vss_search
                cursor.execute(
                    "INSERT INTO symbol_vectors (rowid, embedding) VALUES (?, ?)",
                    (symbol_id, vector_json)
                )
            except sqlite3.OperationalError as e:
                # If virtual table fails, log or ignore since we have python fallback
                pass
                
    conn.commit()
    print(f"Successfully indexed {len(symbols_to_insert)} symbols.")
