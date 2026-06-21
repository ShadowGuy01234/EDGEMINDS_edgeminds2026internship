import sqlite3
import json
import os
import re
from typing import List, Dict, Any, Tuple, Optional

def extract_signature_and_summary(code: str, language: str) -> Tuple[str, str]:
    if not code:
        return "", ""
        
    lines = code.splitlines()
    if not lines:
        return "", ""
        
    signature = lines[0].strip()
    summary = ""
    
    if language == "python":
        sig_parts = []
        for line in lines:
            sig_parts.append(line.strip())
            if ":" in line:
                break
        signature = " ".join(sig_parts)
    else: # JS/TS
        sig_parts = []
        for line in lines:
            sig_parts.append(line.strip())
            if "{" in line or "=>" in line:
                break
        signature = " ".join(sig_parts)
        if signature.endswith("{"):
            signature = signature[:-1].strip()
            
    # Clean up excess spaces in signature
    signature = re.sub(r'\s+', ' ', signature)
            
    doc_lines = []
    in_docstring = False
    docstring_char = None
    
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
            
        if language == "python":
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_docstring = True
                    docstring_char = '"""' if stripped.startswith('"""') else "'''"
                    content = stripped[3:]
                    if content.endswith(docstring_char) and len(content) >= 3:
                        doc_lines.append(content[:-3].strip())
                        break
                    else:
                        doc_lines.append(content.strip())
                elif stripped.startswith("#"):
                    doc_lines.append(stripped[1:].strip())
                else:
                    break
            else:
                if stripped.endswith(docstring_char):
                    doc_lines.append(stripped[:-3].strip())
                    break
                else:
                    doc_lines.append(stripped.strip())
        else: # TS/JS
            if stripped.startswith("/**") or stripped.startswith("/*"):
                in_docstring = True
                content = stripped.replace("/**", "").replace("/*", "").strip()
                if "*/" in stripped:
                    doc_lines.append(content.replace("*/", "").strip())
                    break
                else:
                    if content:
                        doc_lines.append(content)
            elif in_docstring:
                if "*/" in stripped:
                    content = stripped.replace("*/", "").strip()
                    if content.startswith("*"):
                        content = content[1:].strip()
                    if content:
                        doc_lines.append(content)
                    break
                else:
                    content = stripped
                    if content.startswith("*"):
                        content = content[1:].strip()
                    doc_lines.append(content)
            elif stripped.startswith("//"):
                doc_lines.append(stripped[2:].strip())
            else:
                break
                
    summary = " ".join([d for d in doc_lines if d]).strip()
    # Remove leading/trailing quotes and asterisks
    summary = re.sub(r'^[*"\']+|[*"\']+$', '', summary).strip()
    
    if len(summary) > 120:
        summary = summary[:117] + "..."
        
    return signature, summary

def insert_symbols(conn: sqlite3.Connection, blueprints: List[Dict[str, Any]], embedder, has_vss: bool, repo_path: Optional[str] = None):
    """
    Extracts all symbols (functions, classes, exports) from blueprints,
    generates embeddings in batch, and stores them in both symbols and virtual tables.
    Also extracts and indexes signature and docstring summary.
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
        
        # Read file code once per blueprint to slice symbols
        file_content = ""
        full_path = os.path.join(repo_path, file_path) if repo_path else file_path
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    file_content = f.read()
            except Exception:
                pass
                
        file_lines = file_content.splitlines() if file_content else []
        
        def get_slice(start, end):
            if not file_lines or start is None or end is None:
                return ""
            # 1-indexed, inclusive
            return "\n".join(file_lines[start-1:end])
        
        # 1. Functions
        for func in bp.get("functions", []):
            spans = symbol_line_spans.get(func, {})
            start, end = spans.get("start_line"), spans.get("end_line")
            code_slice = get_slice(start, end)
            sig, sum_text = extract_signature_and_summary(code_slice, language)
            symbols_to_insert.append((
                file_path, func, "function", language, layer, 
                start, end, sig, sum_text
            ))
            
        # 2. Classes
        for cls in bp.get("classes", []):
            spans = symbol_line_spans.get(cls, {})
            start, end = spans.get("start_line"), spans.get("end_line")
            code_slice = get_slice(start, end)
            sig, sum_text = extract_signature_and_summary(code_slice, language)
            symbols_to_insert.append((
                file_path, cls, "class", language, layer, 
                start, end, sig, sum_text
            ))
            
        # 3. Exports
        for exp in bp.get("exports", []):
            spans = symbol_line_spans.get(exp, {})
            start, end = spans.get("start_line"), spans.get("end_line")
            code_slice = get_slice(start, end)
            sig, sum_text = extract_signature_and_summary(code_slice, language)
            symbols_to_insert.append((
                file_path, exp, "export", language, layer, 
                start, end, sig, sum_text
            ))
            
    if not symbols_to_insert:
        return
        
    # Extract unique name strings to embed
    names = [item[1] for item in symbols_to_insert]
    
    print(f"Batch embedding {len(names)} symbols...")
    vectors = embedder.embed_batch(names)
    
    # Insert symbols and their corresponding vectors
    for (file_path, name, kind, language, layer, start_line, end_line, sig, sum_text), vector in zip(symbols_to_insert, vectors):
        vector_json = json.dumps(vector)
        
        cursor.execute(
            """
            INSERT INTO symbols (file_path, name, kind, language, layer, embedding, start_line, end_line, signature, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (file_path, name, kind, language, layer, vector_json, start_line, end_line, sig, sum_text)
        )
        symbol_id = cursor.lastrowid
        
        if has_vss:
            try:
                cursor.execute(
                    "INSERT INTO symbol_vectors (rowid, embedding) VALUES (?, ?)",
                    (symbol_id, vector_json)
                )
            except sqlite3.OperationalError:
                pass
                
    conn.commit()
    print(f"Successfully indexed {len(symbols_to_insert)} symbols.")
