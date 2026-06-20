import sqlite3
from typing import Dict, List, Any, Set

def graph_trace(conn: sqlite3.Connection, file_path: str, depth: int = 3) -> Dict[str, Any]:
    """
    Performs BFS traversal of internal import edges.
    Returns:
      - dependents: files importing file_path up to `depth` hops (upstream)
      - dependencies: files imported by file_path up to `depth` hops (downstream)
      - depth_capped: True if there were unvisited edges beyond the depth limit
    """
    cursor = conn.cursor()
    
    # 1. BFS Upstream (Dependents - who imports file_path?)
    dependents: List[Dict[str, Any]] = []
    visited_up: Set[str] = {file_path}
    queue_up = [(file_path, 0)]
    depth_capped = False
    
    while queue_up:
        curr, curr_depth = queue_up.pop(0)
        
        if curr_depth >= depth:
            # Check if there are unvisited adjacent nodes
            cursor.execute(
                "SELECT source_file FROM edges WHERE target_name = ? AND import_type = 'internal'",
                (curr,)
            )
            adj = [row[0] for row in cursor.fetchall()]
            if any(node not in visited_up for node in adj):
                depth_capped = True
            continue
            
        cursor.execute(
            "SELECT source_file FROM edges WHERE target_name = ? AND import_type = 'internal'",
            (curr,)
        )
        for row in cursor.fetchall():
            dep_file = row[0]
            if dep_file not in visited_up:
                visited_up.add(dep_file)
                dependents.append({
                    "file_path": dep_file,
                    "hop": curr_depth + 1
                })
                queue_up.append((dep_file, curr_depth + 1))
                
    # 2. BFS Downstream (Dependencies - who does file_path import?)
    dependencies: List[Dict[str, Any]] = []
    visited_down: Set[str] = {file_path}
    queue_down = [(file_path, 0)]
    
    while queue_down:
        curr, curr_depth = queue_down.pop(0)
        
        if curr_depth >= depth:
            # Check if there are unvisited adjacent nodes
            cursor.execute(
                "SELECT target_name FROM edges WHERE source_file = ? AND import_type = 'internal'",
                (curr,)
            )
            adj = [row[0] for row in cursor.fetchall()]
            if any(node not in visited_down for node in adj):
                depth_capped = True
            continue
            
        cursor.execute(
            "SELECT target_name FROM edges WHERE source_file = ? AND import_type = 'internal'",
            (curr,)
        )
        for row in cursor.fetchall():
            indep_file = row[0]
            if indep_file not in visited_down:
                visited_down.add(indep_file)
                dependencies.append({
                    "file_path": indep_file,
                    "hop": curr_depth + 1
                })
                queue_down.append((indep_file, curr_depth + 1))
                
    return {
        "dependents": dependents,
        "dependencies": dependencies,
        "depth_capped": depth_capped
    }
