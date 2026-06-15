import os
import sqlite3
import json
import httpx
import time
from typing import Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    DB_PATH,
    API_HOST,
    API_PORT,
    FRONTEND_STATIC_DIR,
    ENV
)
from indexer.db import init_db, get_connection
from indexer import embedder
from parser.ingest import ingest_repository
from indexer.build import build_index
from router.slm_router import call_ollama
from engine.executor import execute

# Initialize FastAPI App
app = FastAPI(
    title="CodeGenome-Edge",
    description="Local-only, offline-first codebase intelligence tool",
    version="1.1"
)

# Custom Exception Handler to match F5.5 specification error contract
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
        
    error_code = "error"
    if exc.status_code == 404:
        error_code = "repo_not_found"
    elif exc.status_code == 500:
        error_code = "internal_error"
        
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "message": str(detail),
            "code": exc.status_code
        }
    )

# Pydantic Schemas for requests
class IngestRequest(BaseModel):
    repo_path: str

class QueryRequest(BaseModel):
    query: str

# Database Connection Dependency
def get_db():
    conn, _ = get_connection(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

# Helper to ping Ollama on startup/status check
async def ping_ollama() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False

# Lifespan events
@app.on_event("startup")
async def startup_event():
    print(f"--- CodeGenome-Edge Starting Up ---")
    
    # 1. Initialize SQLite Database Tables
    print(f"Opening database connection to: {DB_PATH}")
    init_db(DB_PATH)
    
    # 2. Pre-load Embeddings Model in memory
    print("Loading SentenceTransformer model...")
    embedder.get_model()
    
    # 3. Verify Ollama connectivity
    ollama_ok = await ping_ollama()
    if not ollama_ok:
        print(f"Warning: Ollama at '{OLLAMA_BASE_URL}' is not reachable.")
    else:
        print(f"Ollama connected successfully. Model: {OLLAMA_MODEL}")
        
    print("CodeGenome-Edge API ready.")
    print(f"-----------------------------------")

# Setup CORS middleware
if ENV == "prod":
    # Allows requests from local network subnets
    origins = ["*"]
else:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True if "*" not in origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.post("/ingest")
def ingest(payload: IngestRequest, db: sqlite3.Connection = Depends(get_db)):
    """
    Triggers repository scanning and index building for a repository path.
    """
    repo_path = payload.repo_path
    if not os.path.exists(repo_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Path '{repo_path}' does not exist on disk"
        )
        
    # Run AST parser
    parser_res = ingest_repository(repo_path, "./index")
    if parser_res.get("status") != "success":
        raise HTTPException(
            status_code=500,
            detail=f"Parsing failed: {parser_res.get('message', 'Unknown error')}"
        )
        
    # Run DB index builder
    build_res = build_index("./index/manifest.json", DB_PATH)
    if build_res.get("status") != "success":
        raise HTTPException(
            status_code=500,
            detail="Database indexing failed"
        )
        
    # Save the repo path to settings table
    cursor = db.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('repo_path', ?)", (repo_path,))
    db.commit()
    
    total_time = parser_res["duration_ms"] + build_res["duration_ms"]
    return {
        "status": "success",
        "files_parsed": parser_res["files_parsed"],
        "files_failed": parser_res["files_failed"],
        "symbols_indexed": build_res["symbols_indexed"],
        "duration_ms": total_time
    }

@app.post("/query")
def query_codebase(payload: QueryRequest, db: sqlite3.Connection = Depends(get_db)):
    """
    Executes a natural language code query, runs intent routing, executes searches,
    and records results in history.
    """
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    # Check if index is built (needs at least one node)
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM nodes")
    if cursor.fetchone()[0] == 0:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "index_not_built",
                "message": "No files are indexed yet. Please run ingestion first.",
                "code": 400
            }
        )
        
    # 1. Route the query using Ollama SLM
    decision = call_ollama(query_text)
    
    # 2. Execute Graph/Vector searches
    trace_result = execute(db, embedder, decision)
    # Ensure correct query text is set
    trace_result["query"] = query_text
    
    # 3. Log results to history table
    cursor.execute(
        """
        INSERT INTO query_history (query, tool_used, routed_by, seed_file, result_json, execution_ms)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            query_text,
            trace_result["tool_used"],
            trace_result["routed_by"],
            trace_result["seed"]["file_path"] if trace_result["seed"] else None,
            json.dumps(trace_result),
            trace_result["execution_ms"]
        )
    )
    db.commit()
    
    return trace_result

@app.get("/status")
async def get_status(db: sqlite3.Connection = Depends(get_db)):
    """
    Returns system status, model information, index stats, and memory usage.
    """
    cursor = db.cursor()
    index_loaded = False
    total_files = 0
    total_symbols = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nodes")
        total_files = cursor.fetchone()[0]
        index_loaded = (total_files > 0)
        
        cursor.execute("SELECT COUNT(*) FROM symbols")
        total_symbols = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        pass
        
    repo_path = ""
    try:
        cursor.execute("SELECT value FROM settings WHERE key = 'repo_path'")
        row = cursor.fetchone()
        if row:
            repo_path = row[0]
    except sqlite3.OperationalError:
        pass
        
    # Check if Ollama is running
    ollama_reachable = await ping_ollama()
    
    # Get memory usage in MB
    memory_used_mb = 0
    sys_mem_used_mb = 0
    sys_mem_total_mb = 0
    sys_mem_percent = 0.0
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_used_mb = int(process.memory_info().rss / 1024 / 1024)
        
        virtual_mem = psutil.virtual_memory()
        sys_mem_used_mb = int(virtual_mem.used / 1024 / 1024)
        sys_mem_total_mb = int(virtual_mem.total / 1024 / 1024)
        sys_mem_percent = virtual_mem.percent
    except Exception:
        pass
        
    return {
        "index_loaded": index_loaded,
        "repo_path": repo_path,
        "total_files": total_files,
        "total_symbols": total_symbols,
        "ollama_reachable": ollama_reachable,
        "ollama_model": OLLAMA_MODEL,
        "memory_used_mb": memory_used_mb,
        "sys_mem_used_mb": sys_mem_used_mb,
        "sys_mem_total_mb": sys_mem_total_mb,
        "sys_mem_percent": sys_mem_percent,
        "env": ENV
    }

@app.get("/files")
def get_files(db: sqlite3.Connection = Depends(get_db)):
    """
    Lists all indexed files with details on functions, classes, and exports counts.
    """
    cursor = db.cursor()
    try:
        cursor.execute("SELECT file_path, language, functions, classes, exports FROM nodes")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return {"files": []}
        
    files = []
    for path, lang, f_json, c_json, e_json in rows:
        try:
            fn_cnt = len(json.loads(f_json)) if f_json else 0
            cls_cnt = len(json.loads(c_json)) if c_json else 0
            exp_cnt = len(json.loads(e_json)) if e_json else 0
        except Exception:
            fn_cnt = cls_cnt = exp_cnt = 0
            
        files.append({
            "path": path,
            "language": lang,
            "function_count": fn_cnt,
            "class_count": cls_cnt,
            "export_count": exp_cnt
        })
        
    return {"files": files}

@app.get("/history")
def get_history(db: sqlite3.Connection = Depends(get_db)):
    """
    Returns a summary list of the last 20 queries executed.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT id, query, tool_used, routed_by, seed_file, execution_ms, created_at, result_json
            FROM query_history
            ORDER BY id DESC
            LIMIT 20
            """
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return {"history": []}
        
    history = []
    for id_val, query, tool, routed, seed, exec_time, created_at, result_json in rows:
        try:
            result = json.loads(result_json) if result_json else None
        except Exception:
            result = None
            
        history.append({
            "id": id_val,
            "query": query,
            "tool_used": tool,
            "routed_by": routed,
            "seed_file": seed,
            "execution_ms": exec_time,
            "timestamp": created_at,
            "result": result
        })
        
    return {"history": history}

# Serve static files if FRONTEND_STATIC_DIR is provided
if FRONTEND_STATIC_DIR:
    from fastapi.staticfiles import StaticFiles
    if os.path.exists(FRONTEND_STATIC_DIR):
        print(f"Serving static files from: {os.path.abspath(FRONTEND_STATIC_DIR)}")
        app.mount("/", StaticFiles(directory=FRONTEND_STATIC_DIR, html=True))
    else:
        print(f"Warning: FRONTEND_STATIC_DIR '{FRONTEND_STATIC_DIR}' does not exist at '{os.path.abspath(FRONTEND_STATIC_DIR)}'.")
