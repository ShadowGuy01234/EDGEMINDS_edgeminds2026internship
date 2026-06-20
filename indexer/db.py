import sqlite3
import os
import json
from typing import Tuple

# Global variable to check if sqlite-vss is loaded
HAS_VSS = False

def get_connection(db_path: str) -> Tuple[sqlite3.Connection, bool]:
    """
    Establishes a connection to the SQLite database and attempts to load sqlite-vss.
    Returns the connection object and a boolean indicating if VSS is successfully loaded.
    """
    global HAS_VSS
    
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # Enable extension loading and try to load sqlite-vss
    has_vss = False
    try:
        import sqlite_vss
        conn.enable_load_extension(True)
        sqlite_vss.load(conn)
        has_vss = True
    except Exception as e:
        # Silently fail, fallback to pure Python vector search is handled downstream
        pass
        
    HAS_VSS = has_vss
    return conn, has_vss

def init_db(db_path: str) -> sqlite3.Connection:
    """
    Initializes the SQLite database with nodes, edges, symbols, settings, and query history tables.
    Also sets up the sqlite-vss virtual table if the extension is available.
    """
    conn, has_vss = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. Create nodes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE NOT NULL,
        language TEXT NOT NULL,
        functions TEXT,   -- JSON array of strings
        classes TEXT,     -- JSON array of strings
        exports TEXT,     -- JSON array of strings
        layer TEXT DEFAULT 'unknown',
        file_hash TEXT
    )
    """)
    
    # 2. Create edges table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file TEXT NOT NULL,
        target_name TEXT NOT NULL,
        import_type TEXT NOT NULL  -- 'internal' | 'external'
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_file)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_name)")
    
    # 3. Create symbols table
    # We include 'embedding' TEXT column to store the 384-dim vector as a JSON list for Python fallback
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,  -- 'function' | 'class' | 'export'
        language TEXT NOT NULL,
        layer TEXT DEFAULT 'unknown',
        embedding TEXT,      -- JSON array of floats (used as fallback vector index)
        start_line INTEGER,
        end_line INTEGER
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_path)")
    
    # 4. Create settings table for state persistence (e.g. repo_path)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # 5. Create query history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        tool_used TEXT,
        routed_by TEXT,
        seed_file TEXT,
        result_json TEXT,     -- Full TraceResult as JSON blob
        execution_ms INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 6. Create sqlite-vss virtual table if extension is loaded
    if has_vss:
        try:
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS symbol_vectors USING vss0(embedding(384))")
        except sqlite3.OperationalError:
            # Table might already exist or there could be a schema discrepancy
            pass
            
    # Dynamic schema migrations for existing databases
    try:
        cursor.execute("ALTER TABLE nodes ADD COLUMN layer TEXT DEFAULT 'unknown'")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE nodes ADD COLUMN file_hash TEXT")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE symbols ADD COLUMN layer TEXT DEFAULT 'unknown'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE symbols ADD COLUMN start_line INTEGER")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE symbols ADD COLUMN end_line INTEGER")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    return conn
