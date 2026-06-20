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
        layer = bp.get("layer", "unknown")
        symbol_line_spans = bp.get("symbol_line_spans", {})
        
        # 1. Functions
        for func in bp.get("functions", []):
            spans = symbol_line_spans.get(func, {})
            symbols_to_insert.append((
                file_path, func, "function", language, layer, 
                spans.get("start_line"), spans.get("end_line")
            ))
            
        # 2. Classes
        for cls in bp.get("classes", []):
            spans = symbol_line_spans.get(cls, {})
            symbols_to_insert.append((
                file_path, cls, "class", language, layer, 
                spans.get("start_line"), spans.get("end_line")
            ))
            
        # 3. Exports
        for exp in bp.get("exports", []):
            spans = symbol_line_spans.get(exp, {})
            symbols_to_insert.append((
                file_path, exp, "export", language, layer, 
                spans.get("start_line"), spans.get("end_line")
            ))
            
    if not symbols_to_insert:
        return
        
    # Extract unique name strings to embed
    names = [item[1] for item in symbols_to_insert]
    
    print(f"Batch embedding {len(names)} symbols...")
    vectors = embedder.embed_batch(names)
    
    # Insert symbols and their corresponding vectors
    for (file_path, name, kind, language, layer, start_line, end_line), vector in zip(symbols_to_insert, vectors):
        vector_json = json.dumps(vector)
        
        cursor.execute(
            """
            INSERT INTO symbols (file_path, name, kind, language, layer, embedding, start_line, end_line)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (file_path, name, kind, language, layer, vector_json, start_line, end_line)
        )
        symbol_id = cursor.lastrowid
        
        if has_vss:
            try:
                # Convert list of floats to serialized raw bytes/JSON for sqlite-vss
                cursor.execute(
                    "INSERT INTO symbol_vectors (rowid, embedding) VALUES (?, ?)",
                    (symbol_id, vector_json)
                )
            except sqlite3.OperationalError as e:
                # If virtual table fails, log or ignore since we have python fallback
                pass
                
    conn.commit()
    print(f"Successfully indexed {len(symbols_to_insert)} symbols.")
