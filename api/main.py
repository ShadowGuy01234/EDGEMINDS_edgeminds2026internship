import os
import sqlite3
import json
import httpx
import time
from typing import Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
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
from retriever.raw_slicer import get_raw_source_slice

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
def ingest(payload: IngestRequest, background_tasks: BackgroundTasks, db: sqlite3.Connection = Depends(get_db)):
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
    
    # 2. Detect layer filter from query text
    layer_filter = None
    q_lower = query_text.lower()
    if any(w in q_lower for w in ["backend", "server", "api", "middleware", "route", "routes", "controller", "controllers", "db", "database", "service", "services"]):
        layer_filter = "backend"
    elif any(w in q_lower for w in ["frontend", "ui", "client", "component", "components", "page", "pages", "view", "views", "react", "hook", "hooks"]):
        layer_filter = "frontend"
        
    # 3. Execute Graph/Vector searches
    trace_result = execute(db, embedder, decision, layer_filter=layer_filter)
    # Ensure correct query text and layer filter are set
    trace_result["query"] = query_text
    trace_result["layer_filter"] = layer_filter
    
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


class ExplainRequest(BaseModel):
    query: str
    tool_used: str
    seed: dict = None
    dependents: list = []
    dependencies: list = []
    symbol_matches: list = []


@app.post("/query/explain")
async def explain_query(payload: ExplainRequest):
    """
    Streams a natural language explanation of the query trace results.
    """
    # 1. Serialize the trace results
    context_lines = []
    context_lines.append(f"Query: {payload.query}")
    context_lines.append(f"Search Method: {payload.tool_used}")
    if payload.seed:
        context_lines.append(f"Anchor Seed: {payload.seed.get('symbol', 'file')} in {payload.seed.get('file_path')} (type: {payload.seed.get('kind', 'file')})")
    if payload.dependents:
        context_lines.append("Upstream Dependents (files importing seed):")
        for d in payload.dependents:
            context_lines.append(f" - {d.get('file_path')} ({d.get('hop')} hops away)")
    if payload.dependencies:
        context_lines.append("Downstream Dependencies (seed imports):")
        for d in payload.dependencies:
            context_lines.append(f" - {d.get('file_path')} ({d.get('hop')} hops away)")
    if payload.symbol_matches:
        context_lines.append("Semantic symbol matches:")
        for m in payload.symbol_matches[:5]:  # Limit to top 5 for context length
            context_lines.append(f" - {m.get('name')} in {m.get('file_path')} ({m.get('kind')}, similarity: {int(m.get('similarity', 0)*100)}%)")
            
    context_str = "\n".join(context_lines)
    
    system_instruction = (
        "You are CodeGenome-Edge, a codebase search assistant. "
        "Your task is to answer the user's codebase query directly using the search results context provided. "
        "Never explain how the search tool works (do not mention vector search, graph search, similarity, or seed/anchor). "
        "Focus on the code facts: state where the symbols/files are located and name the other files that import or depend on them as shown in the context. "
        "Be clear, factual, and extremely concise (maximum 3 sentences). "
        "Do not write JSON, output clean raw text only."
    )
    
    prompt = (
        f"Search Results Context:\n{context_str}\n\n"
        f"User Query: {payload.query}\n\n"
        "Direct Answer:"
    )
    
    ollama_payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": 120,
            "num_ctx": 2048
        },
        "stream": True
    }
    
    async def stream_generator():
        url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        # Use 15 second timeout to allow Ollama to start generating
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                async with client.stream("POST", url, json=ollama_payload) as response:
                    if response.status_code != 200:
                        yield f"Error: Ollama returned status code {response.status_code}"
                        return
                        
                    async for chunk in response.aiter_text():
                        for line in chunk.split("\n"):
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    content = data.get("message", {}).get("content", "")
                                    if content:
                                        yield content
                                except Exception:
                                    pass
            except Exception as e:
                yield f"Error generating explanation: {str(e)}"
                 
    return StreamingResponse(stream_generator(), media_type="text/plain")


class SymbolRequest(BaseModel):
    file_path: str
    symbol_name: str
    kind: str

@app.post("/symbol/explain")
def explain_symbol(payload: SymbolRequest, db: sqlite3.Connection = Depends(get_db)):
    """
    On-demand, streaming explanation of a specific symbol inside a file.
    Streams back a Markdown-formatted explanation.
    """
    cursor = db.cursor()
    cursor.execute(
        "SELECT start_line, end_line, language FROM symbols WHERE file_path = ? AND name = ? AND kind = ?",
        (payload.file_path, payload.symbol_name, payload.kind)
    )
    row = cursor.fetchone()
    if not row:
        cursor.execute(
            "SELECT start_line, end_line, language FROM symbols WHERE file_path = ? AND name = ?",
            (payload.file_path, payload.symbol_name)
        )
        row = cursor.fetchone()
        
    start_line, end_line, language = row if row else (None, None, "python")
    
    cursor.execute("SELECT value FROM settings WHERE key = 'repo_path'")
    repo_row = cursor.fetchone()
    repo_path = repo_row[0] if repo_row else ""
    full_path = os.path.join(repo_path, payload.file_path) if repo_path else payload.file_path
    
    code = get_raw_source_slice(full_path, start_line, end_line)
    
    prompt = f"""You are an expert code analyst. Explain the following {payload.kind} named `{payload.symbol_name}`.

Source Code:
```{language}
{code}
```

Provide a concise explanation using STRICT standard Markdown. 
Use ATX headers (e.g., `## Purpose`). 
DO NOT use Setext headers (DO NOT underline text with `===` or `---`).
DO NOT wrap headers in bold asterisks.

## Purpose
[What this code does]

## Key Logic
[Step-by-step breakdown]

## Context
[How it fits into the file/module]
"""
    
    system_instruction = "You are a precise codebase search assistant. Explain the code in clear, concise Markdown. Do NOT use JSON."
    
    async def event_generator():
        url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        ollama_payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "options": {
                "temperature": 0.1,
                "num_predict": 400,
                "num_ctx": 4096
            },
            "stream": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", url, json=ollama_payload) as response:
                    if response.status_code != 200:
                        err_text = f"Ollama HTTP error {response.status_code}"
                        yield f"data: {json.dumps({'error': err_text})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                        
                    async for chunk in response.aiter_text():
                        for line in chunk.split("\n"):
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    content = data.get("message", {}).get("content", "")
                                    if content:
                                        yield f"data: {json.dumps({'chunk': content})}\n\n"
                                except Exception:
                                    pass
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
        yield "data: [DONE]\n\n"
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Serve static files if FRONTEND_STATIC_DIR is provided
if FRONTEND_STATIC_DIR:
    from fastapi.staticfiles import StaticFiles
    if os.path.exists(FRONTEND_STATIC_DIR):
        print(f"Serving static files from: {os.path.abspath(FRONTEND_STATIC_DIR)}")
        app.mount("/", StaticFiles(directory=FRONTEND_STATIC_DIR, html=True))
    else:
        print(f"Warning: FRONTEND_STATIC_DIR '{FRONTEND_STATIC_DIR}' does not exist at '{os.path.abspath(FRONTEND_STATIC_DIR)}'.")
