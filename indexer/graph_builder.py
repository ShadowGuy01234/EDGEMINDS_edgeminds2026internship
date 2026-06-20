import os
import json
import sqlite3
from typing import List, Dict, Any, Optional, Set

def insert_nodes(conn: sqlite3.Connection, blueprints: List[Dict[str, Any]]):
    """
    Inserts file blueprints into the nodes table.
    """
    cursor = conn.cursor()
    # Clear existing nodes
    cursor.execute("DELETE FROM nodes")
    
    for bp in blueprints:
        cursor.execute(
            """
            INSERT OR REPLACE INTO nodes (file_path, language, functions, classes, exports, layer, file_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bp["file_path"],
                bp["language"],
                json.dumps(bp.get("functions", [])),
                json.dumps(bp.get("classes", [])),
                json.dumps(bp.get("exports", [])),
                bp.get("layer", "unknown"),
                bp.get("file_hash")
            )
        )
    conn.commit()

def resolve_import_path(source_file: str, import_module: str, known_paths: Set[str]) -> Optional[str]:
    """
    Resolves an import module string to a file path within the repository if it exists.
    Returns the file path if resolved (internal), otherwise None (external).
    """
    # Quick check if it's already an exact match
    if import_module in known_paths:
        return import_module
        
    source_dir = os.path.dirname(source_file)
    
    # 1. Handle Python imports
    if source_file.endswith(".py"):
        # Relative import: e.g. from .auth import user -> module is '.auth'
        if import_module.startswith("."):
            # Count leading dots
            dot_count = 0
            for char in import_module:
                if char == ".":
                    dot_count += 1
                else:
                    break
            
            # Resolve directory based on dot count
            # 1 dot = current directory, 2 dots = parent, 3 dots = grandparent
            parts = source_dir.split("/") if source_dir else []
            for _ in range(dot_count - 1):
                if parts:
                    parts.pop()
            
            rel_module = import_module[dot_count:]
            module_path = "/".join(parts)
            if rel_module:
                module_path = f"{module_path}/{rel_module.replace('.', '/')}" if module_path else rel_module.replace(".", "/")
        else:
            # Absolute import: e.g. from src.auth import user -> module is 'src.auth'
            module_path = import_module.replace(".", "/")
            
        # Try finding file paths
        candidates = [
            f"{module_path}.py",
            f"{module_path}/__init__.py"
        ]
        for c in candidates:
            # Clean up double slashes or leading slashes
            c = c.strip("/")
            if c in known_paths:
                return c
                
    # 2. Handle TypeScript / JS imports
    elif source_file.endswith((".ts", ".tsx", ".js", ".jsx")):
        module_path = import_module
        
        # Handle path alias e.g. @/components/Header
        if import_module.startswith("@/"):
            module_path = "src/" + import_module[2:]
            
        if module_path.startswith(("./", "../")):
            # Resolve relative path
            # Normalise source_dir path with module_path
            # We can use os.path.normpath, but normalize separator to '/'
            combined = os.path.join(source_dir, module_path)
            normalized = os.path.normpath(combined).replace(os.sep, "/")
            # If normalized starts with "." or "..", clean it
            module_path = normalized.strip("/")
            
        # Try extensions
        candidates = [
            module_path,
            f"{module_path}.ts",
            f"{module_path}.tsx",
            f"{module_path}.js",
            f"{module_path}.jsx",
            f"{module_path}/index.ts",
            f"{module_path}/index.tsx",
            f"{module_path}/index.js",
            f"{module_path}/index.jsx",
            f"{module_path}.d.ts"
        ]
        for c in candidates:
            c = c.strip("/")
            if c in known_paths:
                return c
                
    return None

def insert_edges(conn: sqlite3.Connection, blueprints: List[Dict[str, Any]]):
    """
    Classifies imports as internal or external and inserts them into the edges table.
    """
    cursor = conn.cursor()
    # Clear existing edges
    cursor.execute("DELETE FROM edges")
    
    known_paths = {bp["file_path"] for bp in blueprints}
    
    for bp in blueprints:
        source_file = bp["file_path"]
        
        for imp in bp.get("imports", []):
            module_name = imp["module"]
            
            # Resolve the import to find if it is internal
            resolved = resolve_import_path(source_file, module_name, known_paths)
            
            if resolved:
                # Internal import
                cursor.execute(
                    """
                    INSERT INTO edges (source_file, target_name, import_type)
                    VALUES (?, ?, ?)
                    """,
                    (source_file, resolved, "internal")
                )
            else:
                # External import
                cursor.execute(
                    """
                    INSERT INTO edges (source_file, target_name, import_type)
                    VALUES (?, ?, ?)
                    """,
                    (source_file, module_name, "external")
                )
    conn.commit()
