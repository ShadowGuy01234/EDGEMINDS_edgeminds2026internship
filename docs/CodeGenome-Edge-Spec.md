# CodeGenome-Edge — Technical Specification Document

**Version:** 1.1  
**Status:** Draft  
**Build Duration:** 8 Weeks  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Environment Strategy: Dev vs Prod](#2-environment-strategy-dev-vs-prod)
3. [System Constraints](#3-system-constraints)
4. [High-Level Architecture](#4-high-level-architecture)
5. [Feature Specifications](#5-feature-specifications)
   - [F1 — AST Parsing Core](#f1--ast-parsing-core)
   - [F2 — Dual-Index Store](#f2--dual-index-store)
   - [F3 — SLM Intent Router](#f3--slm-intent-router)
   - [F4 — Query Execution Engine](#f4--query-execution-engine)
   - [F5 — REST API Layer](#f5--rest-api-layer)
   - [F6 — Frontend Dashboard](#f6--frontend-dashboard)
   - [F7 — Prod: Jetson Deployment](#f7--prod-jetson-deployment)
6. [Data Models](#6-data-models)
7. [API Contract](#7-api-contract)
8. [SLM Prompt Specification](#8-slm-prompt-specification)
9. [Tech Stack Summary](#9-tech-stack-summary)
10. [Out of Scope for v1](#10-out-of-scope-for-v1)
11. [Future Features (Post-Demo)](#11-future-features-post-demo)

---

## 1. Project Overview

CodeGenome-Edge is a local-only, offline-first codebase intelligence tool. It lets engineers query the
structure of any codebase in plain English — without sending a single line of source code to a cloud API.

It does this by:
1. Parsing a repo into a lightweight architectural skeleton (no logic bodies, structure only)
2. Storing the skeleton in a local graph + vector index
3. Using `llama3.2:1b` exclusively as a fast intent classifier and keyword extractor
4. Executing deterministic graph and vector queries based on the model's routing decision
5. Rendering the result as a structured dependency trace on a local web dashboard

### Core Design Philosophy

> The SLM decides **what to look for**. The deterministic engine decides **how to find it**. The template renderer decides **how to show it**.

The 1B model is never asked to generate answers, reason about code, or produce prose. Its only job is
to output a small, structured JSON object. Everything downstream is engineered, not generated. This
makes the system fast, reliable, and verifiable on constrained hardware.

---

## 2. Environment Strategy: Dev vs Prod

The project is built in two clearly separated environments. F1 through F6 are built and validated
entirely on the dev machine. F7 is the Jetson-specific deployment layer that runs only after the full
stack is proven stable on dev.

### Dev Environment

| Property | Value |
|---|---|
| **Machine** | Your local x86/ARM Mac or Linux workstation |
| **OS** | macOS / Ubuntu 22.04 |
| **Ollama** | Local Ollama install, same `llama3.2:1b` model |
| **Purpose** | Build, iterate, test, debug all features |
| **Constraint** | None — full internet, full RAM, fast CPU |
| **Ollama URL** | `http://localhost:11434` |
| **API port** | `http://localhost:8000` |
| **Frontend port** | `http://localhost:5173` (Vite dev server) |

**Everything in F1–F6 is written to be environment-agnostic.** The Ollama base URL, ports, and
file paths are all read from a `.env` file so the same codebase runs on dev and Jetson without
code changes.

### Prod Environment

| Property | Value |
|---|---|
| **Machine** | NVIDIA Jetson Orin Nano 4GB |
| **OS** | Ubuntu 22.04 (JetPack 6) |
| **Ollama** | ARM64 binary, model pre-pulled before air-gap |
| **Purpose** | Demo-day deployment, local network serving |
| **Constraint** | 4GB unified memory, ARM64 arch, no internet |
| **Ollama URL** | `http://172.17.0.1:11434` |
| **API port** | `http://0.0.0.0:8000` (exposed on LAN) |
| **Frontend** | Static build served by FastAPI (no Vite) |

### Environment Config File

A single `.env` file at the project root controls all environment differences:

```env
# .env.dev
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
DB_PATH=./index/codegenome.db
MANIFEST_PATH=./index/manifest.json
API_HOST=127.0.0.1
API_PORT=8000
FRONTEND_STATIC_DIR=          # empty = use Vite dev server separately
ENV=dev

# .env.prod (Jetson)
OLLAMA_BASE_URL=http://172.17.0.1:11434
OLLAMA_MODEL=llama3.2:1b
DB_PATH=/opt/codegenome/index/codegenome.db
MANIFEST_PATH=/opt/codegenome/index/manifest.json
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_STATIC_DIR=/opt/codegenome/frontend/dist
ENV=prod
```

The FastAPI app reads `ENV` on startup and adjusts CORS, static file mounting, and logging accordingly.

### What Changes Between Dev and Prod

| Concern | Dev | Prod (Jetson) |
|---|---|---|
| Ollama install | `ollama` CLI on local machine | ARM64 binary via install script |
| Model pull | `ollama pull llama3.2:1b` on dev machine | Same, done before air-gap |
| Ollama config | Default settings, no tuning needed | `NUM_PARALLEL=1`, `NUM_GPU=999` forced |
| Frontend serving | Vite dev server on `:5173` | Static build served by FastAPI |
| CORS | `localhost` only | Local subnet (e.g., `192.168.1.0/24`) |
| Memory pressure | Not a concern | Actively monitored, capped at 3.2GB |
| Process management | Run manually in terminal | `systemd` services, auto-restart |
| Repo path | Any local folder | Mounted volume at `/mnt/repos/` |
| sqlite-vss build | Pre-built x86 wheel via pip | Must build from source for ARM64 |

> **Note on sqlite-vss on ARM64:** The pip wheel for `sqlite-vss` does not ship ARM64 binaries.
> On Jetson you must build it from source using the Jetson's GCC toolchain. This is a known
> issue — allocate half a day specifically for this in the Jetson setup phase (F7).
> Validate sqlite-vss works on Jetson in Week 1 even if you don't use it yet, so you don't
> discover this problem in Week 7.

---

## 3. System Constraints

### Dev Constraints (relaxed)

| Constraint | Detail |
|---|---|
| **SLM model** | `llama3.2:1b-instruct` via local Ollama. No other models. |
| **SLM role** | Classification and keyword extraction ONLY. No answer generation. |
| **Languages supported (v1)** | Python and TypeScript only |
| **Repo size limit (v1)** | Up to 50,000 lines across all files |
| **Response time target (dev)** | Under 1 second on x86 (used for baseline comparison) |

### Prod Constraints (Jetson)

| Constraint | Detail |
|---|---|
| **Zero outbound network** | No API calls to any external service at runtime |
| **Hardware target** | Jetson Orin Nano 4GB (ARM64, unified memory) |
| **Memory budget** | Total peak RAM must stay under 3.2GB |
| **Response time target (prod)** | Full query → rendered trace under 3 seconds on-device |

### Prod Memory Budget (Jetson)

| Component | Estimated RAM |
|---|---|
| OS + system processes | ~1.2 GB |
| llama3.2:1b via Ollama (Q4_K_M) | ~1.0 GB |
| all-MiniLM-L6-v2 embeddings model | ~90 MB |
| SQLite + sqlite-vss index | ~200 MB |
| FastAPI + Uvicorn | ~80 MB |
| Static frontend (served files) | ~20 MB |
| **Total** | **~2.6 GB** (~1.4 GB headroom) |

---

## 4. High-Level Architecture

### Dev Architecture

```
Developer's Browser
        │
        ├──► http://localhost:5173  (Vite dev server — hot reload)
        │             │ fetch()
        └──► http://localhost:8000  (FastAPI + Uvicorn)
                      │
          ┌───────────┴───────────┐
          │                       │
   localhost:11434          ./index/codegenome.db
   (Ollama, llama3.2:1b)    (SQLite + sqlite-vss)
```

### Prod Architecture (Jetson)

```
┌─────────────────────────────────────────────────────────┐
│                    LOCAL NETWORK                         │
│                                                         │
│   Engineer's Browser ─────► http://<jetson-ip>:8000     │
│                                       │                 │
│                          ┌────────────▼──────────┐      │
│                          │   FastAPI + Uvicorn    │      │
│                          │  serves static React   │      │
│                          │  + handles all APIs    │      │
│                          └──┬──────────────┬──────┘      │
│                             │              │             │
│                  localhost:11434    /opt/codegenome/     │
│                  (Ollama,          index/codegenome.db   │
│                  llama3.2:1b)      (SQLite + sqlite-vss) │
│                                                         │
│                          ┌────────────────────┐         │
│                          │  /mnt/repos/        │         │
│                          │  (repo filesystem)  │         │
│                          └────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

### Request Lifecycle (identical in both environments)

```
User Query (plain English)
        │
        ▼
FastAPI POST /query
        │
        ▼
SLM Router (llama3.2:1b via Ollama)
  → outputs: { tool, keywords }
  → fallback: regex extraction if JSON malformed
        │
        ├── tool = "graph"   → graph_trace()
        ├── tool = "vector"  → vector_search()
        └── tool = "hybrid"  → both, results merged
                │
                ▼
        Query Execution Engine
                │
                ▼
        Trace Object assembled (deterministic)
                │
                ▼
        JSON Response → Frontend renders trace
```

---

## 5. Feature Specifications

---

### F1 — AST Parsing Core

**Purpose:** Ingest a repository folder and extract a lightweight structural skeleton from each source
file. Discard all logic bodies. Output a per-file JSON blueprint.

**Applies to:** Dev and Prod (identical behavior, different repo paths)

#### F1.1 — Language Support (v1)

| Language | Grammar Package | Node Types to Extract |
|---|---|---|
| Python | `tree-sitter-python` | `import_statement`, `import_from_statement`, `function_definition` (name only), `class_definition` (name only) |
| TypeScript | `tree-sitter-typescript` | `import_declaration`, `export_named_declaration`, `function_declaration` (name only), `class_declaration` (name only) |

> Go is deferred to v2. Two grammars is the right scope for the dev + demo timeline.

#### F1.2 — What Gets Extracted (Per File)

```json
{
  "file_path": "src/auth/middleware.py",
  "language": "python",
  "imports": [
    { "module": "jwt", "names": ["decode", "encode"] },
    { "module": "fastapi", "names": ["Request", "HTTPException"] }
  ],
  "exports": ["verify_token", "require_auth"],
  "functions": ["verify_token", "require_auth", "_decode_payload"],
  "classes": ["AuthMiddleware"]
}
```

#### F1.3 — What Gets Discarded

- All lines inside function/method bodies
- Comments and docstrings
- Variable assignments inside functions
- Loop logic, conditionals, arithmetic
- Type annotations beyond function/class names

#### F1.4 — Parser Behavior

- Scan files matching: `*.py`, `*.ts`, `*.tsx`
- Skip directories: `node_modules/`, `.git/`, `__pycache__/`, `dist/`, `build/`, `.venv/`
- Skip files over 500KB
- On parse failure: log to `parse_errors.log`, continue — never crash ingestion
- Produce `manifest.json` listing all successful file blueprints

#### F1.5 — CLI Entrypoint

```bash
python parser/ingest.py --repo /path/to/repo --output ./index/
```

Output structure:
```
index/
  manifest.json       ← array of all file blueprints
  parse_errors.log    ← files that failed, with reason
```

#### F1.6 — Dev Validation Targets

Before moving to F2, validate the parser against three repos:

| Repo | Why |
|---|---|
| `fastapi/fastapi` (GitHub) | Medium Python repo, well-structured |
| `vercel/next.js` (src/ only) | Medium TypeScript repo |
| Your own SessionMate or SatyaSetu codebase | Known ground truth — you can verify correctness manually |

Check: does every function you know exists appear in the manifest? Do imports resolve correctly?

#### F1.7 — Performance Target

| Environment | Target |
|---|---|
| Dev (x86) | 10,000-line repo in under 10 seconds |
| Prod (Jetson) | 10,000-line repo in under 30 seconds |

---

### F2 — Dual-Index Store

**Purpose:** Store the parsed manifest in a single SQLite database with two logical layers — a graph
table for structural file relationships and a vector table for semantic symbol search.

**Applies to:** Dev and Prod (same schema, different DB file paths via `.env`)

#### F2.1 — Single Database File

```
Dev:   ./index/codegenome.db
Prod:  /opt/codegenome/index/codegenome.db
```

Both use identical schema. Path comes from `DB_PATH` in `.env`.

#### F2.2 — Graph Layer Schema

```sql
-- One row per parsed file
CREATE TABLE IF NOT EXISTS nodes (
  id        INTEGER PRIMARY KEY,
  file_path TEXT UNIQUE NOT NULL,
  language  TEXT NOT NULL,
  functions TEXT,   -- JSON array of strings
  classes   TEXT,   -- JSON array of strings
  exports   TEXT    -- JSON array of strings
);

-- One row per import relationship between files
CREATE TABLE IF NOT EXISTS edges (
  id          INTEGER PRIMARY KEY,
  source_file TEXT NOT NULL,
  target_name TEXT NOT NULL,
  import_type TEXT NOT NULL  -- "internal" | "external"
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_file);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_name);
```

**Internal vs External classification:**
- Internal: the imported module name resolves to a file path that exists in `nodes`
- External: third-party package (jwt, fastapi, express, react, etc.)

Only internal edges are used for graph traversal. External edges are stored but not traversed.

#### F2.3 — Vector Layer Schema

Uses `sqlite-vss` for approximate nearest-neighbor vector search on embeddings.

```sql
-- One row per named symbol (function, class, or export)
CREATE TABLE IF NOT EXISTS symbols (
  id        INTEGER PRIMARY KEY,
  file_path TEXT NOT NULL,
  name      TEXT NOT NULL,
  kind      TEXT NOT NULL,  -- "function" | "class" | "export"
  language  TEXT NOT NULL
);

-- Virtual vector table — one row per symbol, linked by rowid
CREATE VIRTUAL TABLE IF NOT EXISTS symbol_vectors USING vss0(
  embedding(384)   -- all-MiniLM-L6-v2 output dimension
);
```

The `symbols.id` and `symbol_vectors` rowid are kept in sync — row N in `symbols` corresponds
to row N in `symbol_vectors`.

#### F2.4 — Embedding Model

Model: `all-MiniLM-L6-v2` via `sentence-transformers`

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
# Loaded once at API startup, kept in memory
# Output: 384-dimensional float32 vector per input string
```

On first run, the model downloads (~90MB). On Jetson, this must be done before air-gapping.
After first download, it is cached locally and requires no internet.

#### F2.5 — Index Builder

```bash
python indexer/build.py --manifest ./index/manifest.json --db ./index/codegenome.db
```

Steps executed in order:
1. Read `manifest.json`, iterate file blueprints
2. Insert each file into `nodes`
3. For each import in each file:
   - Check if `module` or a derivation of it matches any `file_path` in `nodes`
   - If yes → insert edge with `import_type = "internal"`
   - If no → insert edge with `import_type = "external"`
4. For every function, class, and export name across all files:
   - Insert row into `symbols`
   - Generate embedding via `all-MiniLM-L6-v2`
   - Insert vector into `symbol_vectors` at matching rowid
5. Log: total nodes, edges (internal/external split), symbols embedded, duration

#### F2.6 — Incremental Re-index (for changed files)

When a single file changes:
1. Delete from `nodes` where `file_path = changed_file`
2. Delete from `edges` where `source_file = changed_file`
3. Delete from `symbols` where `file_path = changed_file`
4. Delete corresponding rows from `symbol_vectors` (same rowids)
5. Re-parse the file → re-insert all rows → re-embed all symbols

This is triggered manually via `POST /ingest` with a single file path in v1. Auto-watching is v2.

#### F2.7 — Core Query Functions

These two functions are the only interface between the index and the execution engine:

```python
def graph_trace(file_path: str, depth: int = 3) -> dict:
    """
    BFS traversal of the graph index.
    Returns:
      - dependents: files that import file_path, up to `depth` hops upstream
      - dependencies: files that file_path imports, up to `depth` hops downstream
    Each result includes hop distance from seed.
    Stops at depth 3. Sets depth_capped=True if limit hit.
    """

def vector_search(keywords: list[str], top_k: int = 10) -> list[dict]:
    """
    Joins the keyword strings, generates a single embedding,
    runs ANN search on symbol_vectors,
    returns top_k symbols with cosine similarity above 0.35.
    Each result: { name, file_path, kind, similarity }
    """
```

#### F2.8 — Dev Validation

After building the index on a known repo, manually verify:
- `graph_trace("src/auth/middleware.py")` returns expected upstream files
- `vector_search(["JWT", "decode"])` returns `verify_token` or similar as top result
- Re-index on a modified file updates the DB correctly without full rebuild

---

### F3 — SLM Intent Router

**Purpose:** Use `llama3.2:1b` to parse a plain English developer query and output a routing decision —
which query tool to use and what keywords to search for. Nothing else.

**Applies to:** Dev and Prod (identical prompt and logic, same Ollama API)

#### F3.1 — The Model's Exact Job

Input: a raw English query string from the developer  
Output: a JSON object with exactly two fields

```json
{ "tool": "hybrid", "keywords": ["JWT", "middleware"] }
```

That is the entire scope of the model's responsibility. It does not answer the question.
It does not explain anything. It does not touch the codebase.

#### F3.2 — Tool Routing Logic

| Tool value | When to use |
|---|---|
| `"graph"` | Query is about file relationships — what imports what, what breaks if X changes, who depends on Y |
| `"vector"` | Query names a specific function, class, or concept — find it, locate it, show it |
| `"hybrid"` | Query needs both — find a symbol AND trace its relationships (default when unsure) |

#### F3.3 — Ollama Call Configuration

```python
OLLAMA_PARAMS = {
    "model": "llama3.2:1b",       # from OLLAMA_MODEL env var
    "temperature": 0.0,            # must be deterministic
    "num_predict": 80,             # hard cap — JSON object needs ~30 tokens max
    "num_ctx": 512,                # small context = fast inference
    "stop": ["\n\n", "```", "\n}"] # stop tokens prevent prose runoff
}
```

These params are the same in dev and prod. The only difference is the `OLLAMA_BASE_URL`.

#### F3.4 — Fallback Strategy

If the model response:
- Is not valid JSON
- Is missing `tool` or `keywords` fields
- Has `tool` not in `{"graph", "vector", "hybrid"}`
- Times out (>5 seconds)

Then execute fallback:

```python
def fallback_route(query: str) -> RouterDecision:
    STOPWORDS = {
        "where", "does", "what", "how", "is", "the", "a", "an", "in",
        "of", "to", "my", "our", "it", "if", "i", "change", "find",
        "show", "me", "and", "or", "which", "who", "when", "that"
    }
    tokens = query.lower().split()
    keywords = [t for t in tokens if t not in STOPWORDS][:5]
    return RouterDecision(tool="hybrid", keywords=keywords)
```

Log every fallback trigger with the raw model output that caused it.

#### F3.5 — Routing Accuracy Gate

Before integrating the router into the full pipeline, run it against 20 handcrafted test queries.
Target: ≥ 17/20 correct (85%). Do not proceed to F4 integration until this gate is passed.

The 5 examples from Section 8 are the minimum test set. Add 15 more covering edge cases:
queries with typos, very short queries (one word), queries in non-standard phrasing.

#### F3.6 — Routing Metadata

The router always returns a `RouterDecision` object:

```python
@dataclass
class RouterDecision:
    tool: str           # "graph" | "vector" | "hybrid"
    keywords: list[str]
    routed_by: str      # "slm" | "fallback"
    slm_raw: str        # raw model output, for debugging
    latency_ms: int     # time taken for Ollama call
```

`routed_by` is passed through to the API response and shown on the dashboard.

---

### F4 — Query Execution Engine

**Purpose:** Receive the router's decision and execute the appropriate queries against the index.
Assemble a structured trace object. Pure deterministic Python — no model calls in this layer.

**Applies to:** Dev and Prod (identical)

#### F4.1 — Three Execution Paths

**Graph path** (`tool = "graph"`):
1. Run `vector_search(keywords, top_k=3)` to find the most likely seed file
2. Take the top result's `file_path` as seed (highest similarity score)
3. Run `graph_trace(seed_file_path, depth=3)`
4. Return trace with dependents + dependencies, no symbol list

**Vector path** (`tool = "vector"`):
1. Run `vector_search(keywords, top_k=10)`
2. Return matching symbols with file paths and similarity scores
3. No graph traversal

**Hybrid path** (`tool = "hybrid"`):
1. Run `vector_search(keywords, top_k=10)` → get symbol matches
2. Take top result's `file_path` as seed
3. Run `graph_trace(seed_file_path, depth=3)`
4. Return both symbol matches AND graph trace

#### F4.2 — Trace Object

This is the canonical output structure from the execution engine, returned as JSON from the API:

```json
{
  "query": "Where does JWT middleware get called?",
  "routed_by": "slm",
  "tool_used": "hybrid",
  "keywords": ["JWT", "middleware"],
  "slm_latency_ms": 180,
  "seed": {
    "file_path": "src/auth/middleware.py",
    "symbol": "verify_token",
    "kind": "function",
    "similarity": 0.81
  },
  "symbol_matches": [
    { "name": "verify_token", "file_path": "src/auth/middleware.py", "kind": "function", "similarity": 0.81 },
    { "name": "AuthMiddleware", "file_path": "src/auth/middleware.py", "kind": "class", "similarity": 0.74 }
  ],
  "dependents": [
    { "file_path": "src/routes/user.py", "hop": 1 },
    { "file_path": "src/routes/admin.py", "hop": 1 },
    { "file_path": "src/app.py", "hop": 2 }
  ],
  "dependencies": [
    { "file_path": "src/db/session.py", "hop": 1 },
    { "file_path": "src/config.py", "hop": 2 }
  ],
  "depth_capped": false,
  "no_match": false,
  "execution_ms": 240
}
```

#### F4.3 — Edge Cases

| Situation | Behavior |
|---|---|
| Vector search returns no results above 0.35 similarity | Set `no_match: true`, return empty lists, skip graph trace |
| Graph trace hits depth limit | Set `depth_capped: true`, return what was found |
| Seed file has no internal edges | Return symbol matches only, `dependents` and `dependencies` are empty arrays |
| Router returns fallback decision | `routed_by: "fallback"` propagates through to trace output |

---

### F5 — REST API Layer

**Purpose:** FastAPI backend that orchestrates all components, serves the frontend, and persists query
history. Single process. Single port.

**Dev behavior:** Runs on `localhost:8000`, CORS allows `localhost:5173`  
**Prod behavior:** Runs on `0.0.0.0:8000`, CORS allows local subnet, serves static frontend files

#### F5.1 — Startup Sequence

On `uvicorn` start, the app initializes in this order:
1. Load `.env` config
2. Open SQLite connection to `DB_PATH` (error if file doesn't exist)
3. Load `all-MiniLM-L6-v2` into memory (log time taken)
4. Ping Ollama at `OLLAMA_BASE_URL/api/tags` — log warning if not reachable but don't crash
5. If `ENV=prod` and `FRONTEND_STATIC_DIR` is set → mount static files at `/`
6. Log "CodeGenome-Edge ready" with memory usage

#### F5.2 — Endpoints

**`POST /ingest`**  
Trigger repo parsing + index building. Blocking call.
```json
// Request
{ "repo_path": "/path/to/repo" }

// Response
{
  "status": "success",
  "files_parsed": 142,
  "files_failed": 3,
  "symbols_indexed": 891,
  "duration_ms": 18400
}
```

**`POST /query`**  
Submit a natural language query. Returns a Trace Object.
```json
// Request
{ "query": "Where does JWT middleware get called?" }

// Response → Full Trace Object (see F4.2)
```

**`GET /status`**  
System health check. Polled every 5 seconds by the dashboard.
```json
{
  "index_loaded": true,
  "repo_path": "/path/to/repo",
  "total_files": 142,
  "total_symbols": 891,
  "ollama_reachable": true,
  "ollama_model": "llama3.2:1b",
  "memory_used_mb": 1840,
  "env": "dev"
}
```

**`GET /files`**  
List all indexed files.
```json
{
  "files": [
    {
      "path": "src/auth/middleware.py",
      "language": "python",
      "function_count": 4,
      "class_count": 1,
      "export_count": 2
    }
  ]
}
```

**`GET /history`**  
Return last 20 queries with metadata (not full trace, just summary).
```json
{
  "history": [
    {
      "id": 1,
      "query": "Where is JWT handled?",
      "tool_used": "hybrid",
      "routed_by": "slm",
      "seed_file": "src/auth/middleware.py",
      "execution_ms": 240,
      "timestamp": "2025-06-15T14:23:01Z"
    }
  ]
}
```

#### F5.3 — Query History Persistence

Every `/query` call writes to SQLite:

```sql
CREATE TABLE IF NOT EXISTS query_history (
  id           INTEGER PRIMARY KEY,
  query        TEXT NOT NULL,
  tool_used    TEXT,
  routed_by    TEXT,
  seed_file    TEXT,
  result_json  TEXT,     -- full TraceResult as JSON blob
  execution_ms INTEGER,
  created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
```

`GET /history` reads the last 20 rows ordered by `created_at DESC`.

#### F5.4 — Environment-Specific Behavior

```python
# In main.py, after loading .env:

if ENV == "prod" and FRONTEND_STATIC_DIR:
    # Prod: serve built React as static files
    app.mount("/", StaticFiles(directory=FRONTEND_STATIC_DIR, html=True))
    # CORS for local network subnet
    origins = ["http://192.168.1.0/24"]
else:
    # Dev: allow Vite dev server
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"])
```

#### F5.5 — Error Responses

All errors return consistent shape:
```json
{ "error": "repo_not_found", "message": "Path /mnt/repos/xyz does not exist", "code": 404 }
```

Common error codes:
- `repo_not_found` — path doesn't exist
- `index_not_built` — DB file missing, run ingest first
- `ollama_unreachable` — Ollama not running
- `parse_failed` — repo exists but nothing could be parsed
- `no_results` — query ran but returned empty trace

---

### F6 — Frontend Dashboard

**Purpose:** Single-page React app. In dev, runs on Vite dev server with hot reload. In prod, built
to static files and served by FastAPI.

**Dev:** `npm run dev` → `localhost:5173`, API calls go to `localhost:8000`  
**Prod:** `npm run build` → `dist/` folder copied to Jetson, served by FastAPI at `:8000`

#### F6.1 — Layout

```
┌──────────────────────────────────────────────────────────────┐
│  CodeGenome-Edge          [● Dev / ● Prod]  RAM: 1.8GB  ✓   │
├─────────────────┬────────────────────────────────────────────┤
│                 │                                            │
│  Recent         │  Trace Output Panel                        │
│  Queries        │                                            │
│                 │  Seed: verify_token  ← src/auth/middleware │
│  [query 1]  →   │                                            │
│  [query 2]  →   │  DEPENDENTS (3 files)                      │
│  [query 3]  →   │    hop 1 → src/routes/user.py              │
│                 │    hop 1 → src/routes/admin.py             │
│                 │    hop 2 → src/app.py                      │
│                 │                                            │
│                 │  DEPENDENCIES (2 files)                    │
│                 │    hop 1 → src/db/session.py               │
│                 │    hop 2 → src/config.py                   │
│                 │                                            │
│                 │  SYMBOL MATCHES                            │
│                 │    verify_token [fn]  0.81                 │
│                 │    AuthMiddleware [class]  0.74            │
│                 │                                            │
│                 │  ─────────────────────────────             │
│                 │  Routed by: SLM ✓  Tool: hybrid  240ms    │
│                 │                                            │
├─────────────────┴────────────────────────────────────────────┤
│  [ Ask anything about your codebase...             ]  [Ask]  │
└──────────────────────────────────────────────────────────────┘
```

#### F6.2 — Components

**Header Bar**
- App name on the left
- Environment badge: `DEV` (yellow) or `PROD` (green) — read from `/status` response `env` field
- RAM usage: live from `/status`, updated every 5 seconds
- Ollama status dot: green if `ollama_reachable: true`, red if false

**Query Input Bar (bottom)**
- Full-width text input, sticky to bottom
- Submit on Enter or "Ask" button click
- Disabled with spinner while query is in-flight
- After submit: input clears, focus stays on input

**Trace Output Panel (main area)**
- Shows seed symbol + file path as the anchor at the top
- Dependents section: files that depend on the seed, grouped by hop number
- Dependencies section: files the seed depends on, grouped by hop number
- Symbol matches section: all matching symbols with similarity scores and kind badges
- Footer row: `Routed by: SLM ✓` or `Routed by: Fallback ⚠` + tool used + total ms
- Empty state: "Ask a question about your codebase to see results"
- No-match state: "No matching symbols found for: [keywords]"

**Query History Sidebar (left)**
- Last 20 queries as clickable list items
- Each item shows: truncated query text + tool badge
- Clicking an item: re-renders that query's result from stored JSON (no re-query)
- Newest at top

**Ingest Panel (collapsible, top or side)**
- Text input for repo path
- "Ingest" button → calls `POST /ingest` → shows progress bar + result summary
- Shows current indexed repo path from `/status`

#### F6.3 — API Base URL Config

```javascript
// frontend/src/config.js
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
export default API_BASE;
```

In dev: `VITE_API_URL` not set → defaults to `localhost:8000`  
In prod build: `VITE_API_URL=http://<jetson-ip>:8000 npm run build` (or left empty since frontend is served from same origin)

#### F6.4 — Tech Stack

- React 18 + Vite
- Tailwind CSS (utility classes, no component library)
- `fetch` for all API calls (no Axios, no React Query)
- No SSR, no routing library needed (single page)
- No localStorage — all state in React `useState`

#### F6.5 — Dev → Prod Build Process

```bash
# On dev machine
cd frontend
npm install
npm run dev         # development with hot reload

# When ready to deploy to Jetson
VITE_API_URL="" npm run build    # empty = same-origin requests
# Outputs to frontend/dist/

# Transfer to Jetson
scp -r frontend/dist/ user@<jetson-ip>:/opt/codegenome/frontend/dist/
# FastAPI now serves it automatically (ENV=prod)
```

---

### F7 — Prod: Jetson Deployment

**Purpose:** Deploy the validated dev stack onto the Jetson Orin Nano 4GB and expose it on the
local network. This entire feature is Jetson-only. Nothing here is needed during dev.

**Prerequisite:** F1 through F6 must be fully validated on dev before starting F7.

#### F7.1 — Pre-Deployment Checklist (Before Air-Gapping)

Do all of these while the Jetson still has internet access:

- [ ] Install Ollama ARM64 binary: `curl -fsSL https://ollama.com/install.sh | sh`
- [ ] Pull the model: `ollama pull llama3.2:1b`
- [ ] Install Python deps: `pip install fastapi uvicorn sentence-transformers tree-sitter tree-sitter-languages --break-system-packages`
- [ ] Build and install `sqlite-vss` from source (see F7.2)
- [ ] Download `all-MiniLM-L6-v2` model cache by running the embedder once
- [ ] Verify `ollama run llama3.2:1b "say hi"` works on-device
- [ ] Copy project files to `/opt/codegenome/`
- [ ] Copy `frontend/dist/` to `/opt/codegenome/frontend/dist/`
- [ ] Copy `.env.prod` to `/opt/codegenome/.env`

#### F7.2 — sqlite-vss ARM64 Build (Critical)

The `sqlite-vss` pip wheel has no ARM64 binary. Build from source:

```bash
# On Jetson
sudo apt install cmake build-essential libsqlite3-dev
git clone --recursive https://github.com/asg017/sqlite-vss.git
cd sqlite-vss
make loadable
# Produces: dist/vss0.so
# Copy to your project:
cp dist/vss0.so /opt/codegenome/vss0.so
```

In Python, load the extension manually instead of via pip:
```python
import sqlite3
conn = sqlite3.connect("codegenome.db")
conn.enable_load_extension(True)
conn.load_extension("/opt/codegenome/vss0.so")
```

**Validate this works in Week 1 of development, not Week 7.** SSH into Jetson early, build the
extension, and run a basic vector insert + search. This is the highest-risk dependency in the
entire project.

#### F7.3 — Ollama Tuning for 4GB

Edit `/etc/systemd/system/ollama.service`, add to `[Service]`:

```ini
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_NUM_GPU=999"
Environment="OLLAMA_FLASH_ATTENTION=1"
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

`NUM_PARALLEL=1` is the most important setting — it prevents two concurrent Ollama requests from
doubling memory usage. The dashboard must disable the input during in-flight queries (see F6) to
enforce this from the frontend side as well.

#### F7.4 — Systemd Service for FastAPI

Create `/etc/systemd/system/codegenome.service`:

```ini
[Unit]
Description=CodeGenome-Edge API
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/opt/codegenome
EnvironmentFile=/opt/codegenome/.env
ExecStart=/usr/bin/python3 -m uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --log-level info
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable codegenome
sudo systemctl start codegenome
sudo journalctl -u codegenome -f   # watch logs
```

#### F7.5 — Static IP for Jetson

Set a static IP so the local network URL never changes:
```bash
sudo nmcli con mod "Wired connection 1" ipv4.addresses 192.168.1.100/24
sudo nmcli con mod "Wired connection 1" ipv4.method manual
sudo nmcli con up "Wired connection 1"
```

Engineers access the tool at `http://192.168.1.100:8000`.

#### F7.6 — Startup Sequence

1. Power on Jetson
2. `ollama.service` starts → loads `llama3.2:1b` into GPU VRAM (~30s)
3. `codegenome.service` starts → FastAPI initializes, loads embeddings model (~20s)
4. Dashboard available at `http://192.168.1.100:8000`

Cold start to query-ready target: **under 90 seconds**

#### F7.7 — Memory Watchdog

A simple script run via cron every 2 minutes:

```bash
#!/bin/bash
# /opt/codegenome/watchdog.sh
USED=$(free -m | awk 'NR==2{print $3}')
if [ "$USED" -gt 3700 ]; then
  echo "$(date): Memory at ${USED}MB — restarting codegenome service" >> /var/log/codegenome-watchdog.log
  systemctl restart codegenome
fi
```

```bash
# Add to crontab
*/2 * * * * /opt/codegenome/watchdog.sh
```

The `/status` endpoint also reports `memory_used_mb` so the dashboard can show a visual warning
before the watchdog triggers.

#### F7.8 — Demo Day Checklist

Run through this the day before the demo:

- [ ] Cold boot Jetson, time the startup — confirm under 90 seconds
- [ ] Ingest the demo repo (FastAPI source recommended), verify index builds cleanly
- [ ] Run all 5 test queries from Section 8, verify correct routing and trace output
- [ ] Check RAM usage on dashboard during a query — confirm under 3.2GB
- [ ] Simulate a fallback: send a one-word query, confirm fallback triggers and result still renders
- [ ] Connect a second device to the same network, open `http://192.168.1.100:8000`, verify it loads
- [ ] Keep a backup: pre-indexed `codegenome.db` file for the demo repo, in case re-ingest fails on stage

---

## 6. Data Models

### FileBlueprint — Output of parser (F1)

```typescript
interface FileBlueprint {
  file_path: string;
  language: "python" | "typescript";
  imports: Array<{ module: string; names: string[] }>;
  exports: string[];
  functions: string[];
  classes: string[];
}
```

### RouterDecision — Output of SLM router (F3)

```typescript
interface RouterDecision {
  tool: "graph" | "vector" | "hybrid";
  keywords: string[];
  routed_by: "slm" | "fallback";
  slm_raw: string;
  latency_ms: number;
}
```

### TraceResult — Output of execution engine (F4), returned by API (F5)

```typescript
interface TraceResult {
  query: string;
  routed_by: "slm" | "fallback";
  tool_used: "graph" | "vector" | "hybrid";
  keywords: string[];
  slm_latency_ms: number;
  seed: {
    file_path: string;
    symbol: string;
    kind: "function" | "class" | "export";
    similarity: number;
  } | null;
  symbol_matches: Array<{
    name: string;
    file_path: string;
    kind: string;
    similarity: number;
  }>;
  dependents: Array<{ file_path: string; hop: number }>;
  dependencies: Array<{ file_path: string; hop: number }>;
  depth_capped: boolean;
  no_match: boolean;
  execution_ms: number;
}
```

---

## 7. API Contract

| Method | Endpoint | Auth | Input | Output | Dev target | Prod target |
|---|---|---|---|---|---|---|
| POST | `/ingest` | None | `{ repo_path }` | Ingest summary | <20s | <60s |
| POST | `/query` | None | `{ query }` | TraceResult | <500ms | <3s |
| GET | `/status` | None | — | System health | — | — |
| GET | `/files` | None | — | File list | — | — |
| GET | `/history` | None | — | Last 20 queries | — | — |

All responses: `Content-Type: application/json`  
All errors: `{ "error": "<code>", "message": "<detail>", "code": <http_status> }`

---

## 8. SLM Prompt Specification

This is the exact prompt sent to `llama3.2:1b`. Keep it under 200 tokens total.
Do not expand it, do not add examples inline, do not change the output format.

### System Prompt

```
You are a code navigation router. Your only job is to output a JSON routing decision.

Rules:
- Output ONLY a JSON object. No explanation. No preamble. No markdown.
- "tool" must be exactly one of: "graph", "vector", "hybrid"
- "keywords" must be an array of 2 to 5 strings from the user's query
- Use "graph" when the query is about file relationships or what imports what
- Use "vector" when the query names a specific function, class, or module
- Use "hybrid" when unsure or when both apply

Output format:
{"tool": "...", "keywords": ["...", "..."]}
```

### User Turn Template

```
Query: {user_query}
```

### Required Test Suite (minimum 20 queries, 5 shown here)

| Query | Expected tool | Expected keywords (approximate) |
|---|---|---|
| "What files import the auth module?" | `graph` | `["auth", "module"]` |
| "Find the JWT decode function" | `vector` | `["JWT", "decode"]` |
| "Where is rate limiting handled and what depends on it?" | `hybrid` | `["rate", "limiting"]` |
| "Show me the database connection module" | `vector` | `["database", "connection"]` |
| "What breaks if I change the middleware?" | `hybrid` | `["middleware"]` |

Add 15 more before integration. Include: single-word queries, queries with typos, very long
queries (20+ words), queries that don't mention any code concept.

---

## 9. Tech Stack Summary

### Dev Stack

| Layer | Component | Notes |
|---|---|---|
| SLM Runtime | Ollama (local install) | `brew install ollama` or Linux script |
| SLM Model | `llama3.2:1b-instruct` | `ollama pull llama3.2:1b` |
| Parser | `tree-sitter` + `tree-sitter-languages` | pip, x86 wheels available |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) | pip, downloads model on first run |
| Database | `sqlite3` (stdlib) + `sqlite-vss` | pip wheel works on x86 |
| Backend | `fastapi` + `uvicorn` | pip |
| Frontend | React 18 + Vite + Tailwind | npm |

### Prod Stack (Jetson additions/changes)

| Layer | Component | Notes |
|---|---|---|
| SLM Runtime | Ollama ARM64 binary | install script, tune systemd env vars |
| sqlite-vss | Built from source | No ARM64 pip wheel — build with GCC |
| Frontend | Static `dist/` served by FastAPI | No Vite on Jetson |
| Process mgmt | systemd | Two services: ollama + codegenome |

---

## 10. Out of Scope for v1

- Go language parsing (v2)
- Natural language answer generation by SLM
- Change impact heatmap / blast radius scoring
- Circular dependency detection
- Module complexity ranking
- Real-time file watcher / auto re-index
- Exportable Markdown onboarding reports
- Multi-repo support
- User authentication
- C++, Java, Rust support
- Diff-aware structural changelog

---

## 11. Future Features (Post-Demo)

Priority order for v2:

1. **Go language support** — tree-sitter grammar is ARM64-ready
2. **Change Impact Scorer** — blast radius score per file, rendered as heatmap
3. **Circular Dependency Detector** — DFS cycle detection, shown as dashboard warnings
4. **Onboarding Path Generator** — BFS from entry point, ordered reading list for new engineers
5. **Module Complexity Ranking** — top 10 most-coupled files by fan-in + fan-out
6. **Real-time File Watcher** — incremental re-index via `watchdog`
7. **Exportable Report** — one-click Markdown export of current trace
8. **Bounded SLM Summarization** — second model call with controlled input → one-sentence summary
9. **Diff-Aware Changelog** — structural diff between index snapshots
10. **Multi-repo support** — index multiple repos, switch from dashboard

---

*End of Specification — v1.1*
