# CodeGenome-Edge — Task List

**Derived from:** Spec v1.1  
**Total Tasks:** 52  
**Build Duration:** 8 Weeks  
**Convention:** Tasks within each group can be done in the order listed. Cross-group dependencies are listed at the end of each task where relevant.

---

## Task 1 — Project Setup & Environment

**Goal:** Get a working skeleton repo, both environments configured, and Ollama running before writing any feature code.

- **1a** — Create the project folder structure:
  ```
  codegenome-edge/
    parser/
    indexer/
    router/
    engine/
    api/
    frontend/
    index/          ← gitignored, holds DB and manifest
    scripts/
    tests/
    .env.dev
    .env.prod
    .gitignore
    requirements.txt
    README.md
  ```
- **1b** — Create `.env.dev` with all fields from spec Section 2 (OLLAMA_BASE_URL, OLLAMA_MODEL, DB_PATH, MANIFEST_PATH, API_HOST, API_PORT, FRONTEND_STATIC_DIR, ENV)
- **1c** — Create `.env.prod` template with Jetson paths (do not fill Jetson IP yet, mark as TODO)
- **1d** — Create `requirements.txt` with all Python deps: `fastapi`, `uvicorn`, `sentence-transformers`, `tree-sitter`, `tree-sitter-languages`, `sqlite-vss`, `python-dotenv`, `httpx`
- **1e** — Install Ollama on dev machine, pull `llama3.2:1b`: `ollama pull llama3.2:1b`
- **1f** — Verify Ollama is working: `curl http://localhost:11434/api/tags` — confirm `llama3.2:1b` appears in response
- **1g** — Run a smoke test Ollama call from Python using `httpx` — send a simple prompt, confirm JSON response comes back
- **1h** — Create `config.py` in `api/` that reads all env vars from `.env` using `python-dotenv` and exposes them as typed constants — this file is imported by every other module
- **1i** — Initialize a git repo, commit the skeleton, add `index/` and `__pycache__/` and `.env.*` to `.gitignore`

**⚠ Early Jetson task (do in parallel with Task 1, do not skip):**
- **1j** — SSH into Jetson, clone the repo, attempt to build `sqlite-vss` from source using the commands in spec F7.2 — confirm the `.so` file builds successfully. If it fails, debug now, not in Week 7. Log the exact build commands that worked.

---

## Task 2 — AST Parser: Python

**Goal:** Parse Python files into the FileBlueprint JSON format. Complete and validated before touching TypeScript.

*Depends on: 1a, 1d (requirements installed)*

- **2a** — Install and verify `tree-sitter` and `tree-sitter-languages` work on dev machine — write a 5-line script that loads the Python grammar and parses a hello-world `.py` file
- **2b** — Write `parser/python_parser.py`:
  - Accept a file path as input
  - Open the file, run tree-sitter with the Python grammar
  - Extract: all `import_statement` nodes → module name + imported names
  - Extract: all `import_from_statement` nodes → module name + imported names
  - Return partial FileBlueprint (imports only)
- **2c** — Extend `parser/python_parser.py`:
  - Extract: all `function_definition` nodes at module level and class level → name only, skip body
  - Extract: all `class_definition` nodes → name only, skip body
  - Extract: exports (in Python: all names not prefixed with `_` that are functions or classes)
  - Return complete FileBlueprint
- **2d** — Write `parser/file_scanner.py`:
  - Accept a repo root path
  - Walk the directory tree, skipping: `node_modules/`, `.git/`, `__pycache__/`, `dist/`, `build/`, `.venv/`
  - Skip files over 500KB
  - Return a list of all `.py`, `.ts`, `.tsx` file paths found
- **2e** — Write error handling in the parser: wrap each file parse in try/except, on failure write to `parse_errors.log` with the file path and exception message, continue to next file — never raise
- **2f** — Validate Python parser against a real repo: clone `fastapi/fastapi` locally, run the parser on it, open `manifest.json` and manually check 5 known files — confirm their imports, functions, and classes are correct

---

## Task 3 — AST Parser: TypeScript

**Goal:** Extend the parser to handle TypeScript and `.tsx` files, then wire up the full ingest CLI.

*Depends on: 2a, 2b, 2c (Python parser complete)*

- **3a** — Write `parser/typescript_parser.py`:
  - Load tree-sitter TypeScript grammar from `tree-sitter-languages`
  - Extract: `import_declaration` nodes → module name + imported names
  - Extract: `export_named_declaration` nodes → exported names
  - Extract: `function_declaration` nodes at module level → name only
  - Extract: `class_declaration` nodes → name only
  - Return complete FileBlueprint
- **3b** — Handle `.tsx` files: same grammar as TypeScript, but also include JSX component functions (arrow function assignments that are exported) — these are the most common "export" pattern in React
- **3c** — Write `parser/ingest.py` — the main CLI entrypoint:
  - Accept `--repo` and `--output` args
  - Call `file_scanner.py` to get file list
  - Dispatch each file to the correct parser (Python or TypeScript) based on extension
  - Collect all FileBlueprint results into an array
  - Write `manifest.json` to the output directory
  - Print summary: files parsed, files failed, total functions, total classes
- **3d** — Validate TypeScript parser: clone a known Next.js or React project, run ingest, manually check that component exports, hook function names, and import paths are correctly captured
- **3e** — Run ingest on your own `SessionMate` or `SatyaSetu` codebase (known ground truth) — verify results match what you know is in the repo

---

## Task 4 — SQLite Graph Index

**Goal:** Build the graph layer of the database — nodes and edges tables, populated from the manifest.

*Depends on: 2f, 3d (manifest.json validated and correct)*

- **4a** — Write `indexer/db.py`:
  - `init_db(db_path)` — creates the SQLite connection, runs `CREATE TABLE IF NOT EXISTS` for `nodes`, `edges`, `query_history` (from spec F2.2 and F5.3 schemas)
  - Returns a connection object used by all other indexer functions
- **4b** — Write `indexer/graph_builder.py`:
  - `insert_nodes(conn, blueprints)` — bulk insert all FileBlueprint data into `nodes` table, storing functions/classes/exports as JSON strings
  - `classify_import(module_name, known_file_paths)` → returns `"internal"` or `"external"` by checking if the module name matches any known file path (strip extensions, handle relative paths)
  - `insert_edges(conn, blueprints, known_paths)` — for each import in each blueprint, classify it and insert into `edges`
- **4c** — Write `indexer/graph_query.py`:
  - `graph_trace(conn, file_path, depth=3)` — BFS traversal:
    - Upstream pass: find all files in `edges` where `target_name` resolves to `file_path` (dependents), recurse up to `depth` hops
    - Downstream pass: find all files in `edges` where `source_file = file_path` (dependencies), recurse up to `depth` hops
    - Track hop count for each result
    - Stop at depth 3, set `depth_capped=True` if limit hit
    - Return `{ dependents: [...], dependencies: [...], depth_capped: bool }`
- **4d** — Write unit tests for graph queries in `tests/test_graph.py`:
  - Create a small in-memory SQLite DB with 5 known nodes and 4 known edges
  - Assert `graph_trace` returns the correct dependents and dependencies at each hop
  - Assert depth cap triggers correctly
  - Assert a file with no edges returns empty lists

---

## Task 5 — SQLite Vector Index

**Goal:** Build the vector layer — embed all symbol names, store them in sqlite-vss, write the search function.

*Depends on: 4a (db.py and init_db ready)*

- **5a** — Write `indexer/embedder.py`:
  - Load `all-MiniLM-L6-v2` via `sentence-transformers` once at module level (not per call)
  - `embed(text: str) -> list[float]` — returns a 384-dim float list
  - `embed_batch(texts: list[str]) -> list[list[float]]` — batch version for efficiency during index build
  - Log time taken to load model on first import
- **5b** — Extend `indexer/db.py`:
  - Add `CREATE TABLE IF NOT EXISTS symbols` (spec F2.3 schema)
  - Add `CREATE VIRTUAL TABLE IF NOT EXISTS symbol_vectors USING vss0(embedding(384))` 
  - Handle loading the sqlite-vss extension before creating the virtual table: `conn.load_extension("vss0")` — use path from env var `VSS_EXTENSION_PATH`
- **5c** — Write `indexer/vector_builder.py`:
  - `insert_symbols(conn, blueprints, embedder)`:
    - For each blueprint, iterate functions, classes, exports
    - Insert each into `symbols` table, get the auto-incremented `id`
    - Embed the symbol name using `embedder.embed(name)`
    - Insert the embedding into `symbol_vectors` at the matching rowid
  - Use batch embedding (5c→5a) for all names in one repo before inserting — faster than one-by-one
- **5d** — Write `indexer/vector_query.py`:
  - `vector_search(conn, embedder, keywords: list[str], top_k=10) -> list[dict]`:
    - Join keywords into a single string, embed it
    - Run `SELECT rowid, distance FROM symbol_vectors WHERE vss_search(embedding, ?) LIMIT ?`
    - Join result rowids back to `symbols` table to get name, file_path, kind
    - Filter out results with cosine distance above threshold (distance > 0.65 ≈ similarity < 0.35)
    - Return list of `{ name, file_path, kind, similarity }`
- **5e** — Write `indexer/build.py` — the full index build CLI:
  - Accept `--manifest` and `--db` args
  - Call `init_db`, `insert_nodes`, `insert_edges`, `insert_symbols` in order
  - Print final summary: nodes, internal edges, external edges, symbols embedded, total time
- **5f** — Validate the full index: build on the `fastapi/fastapi` repo, then run manual queries:
  - `vector_search(["JWT", "decode"])` — does it return something plausible?
  - `graph_trace("fastapi/routing.py")` — does it return correct dependents?
  - If results look wrong, debug embedding quality or edge classification before continuing

---

## Task 6 — SLM Intent Router

**Goal:** Wire up the llama3.2:1b model as a pure routing layer. Test it in isolation before connecting to anything else.

*Depends on: 1e, 1f, 1g (Ollama working on dev machine)*

- **6a** — Write `router/prompt.py`:
  - Define the system prompt exactly as written in spec Section 8 — store as a module-level constant string
  - Define `build_user_turn(query: str) -> str` — returns `"Query: {query}"`
  - No other logic in this file — prompt is the source of truth, edit here and only here
- **6b** — Write `router/slm_router.py`:
  - `RouterDecision` dataclass with fields: `tool`, `keywords`, `routed_by`, `slm_raw`, `latency_ms`
  - `call_ollama(query: str) -> RouterDecision`:
    - Build the messages array: system prompt + user turn
    - POST to `{OLLAMA_BASE_URL}/api/chat` with params from spec F3.3 (`temperature=0.0`, `num_predict=80`, `num_ctx=512`, `stop` tokens)
    - Parse response JSON, extract the model's message content
    - Try `json.loads()` on the content
    - If valid JSON with correct fields → return `RouterDecision(routed_by="slm", ...)`
    - If any failure → call fallback
- **6c** — Write `router/fallback.py`:
  - `STOPWORDS` set as defined in spec F3.4
  - `fallback_route(query: str, slm_raw: str = "") -> RouterDecision`:
    - Strip stopwords, take up to 5 remaining tokens as keywords
    - Return `RouterDecision(tool="hybrid", keywords=..., routed_by="fallback", slm_raw=slm_raw, ...)`
  - Log every fallback trigger to a file: `logs/router_fallback.log` with timestamp + raw model output
- **6d** — Write `tests/test_router.py` — the routing accuracy test suite:
  - Write all 20 test queries (5 from spec Section 8 + 15 more you write yourself)
  - For each query, call `call_ollama()` and assert the returned `tool` matches the expected value
  - Keywords don't need exact match — assert at least one expected keyword is present
  - Print a result table at the end: query | expected | got | pass/fail
  - **Gate: must pass 17/20 before proceeding to Task 7**
- **6e** — Tune if needed: if accuracy is below 17/20, try minor prompt adjustments (reorder rules, rephrase definitions) — do NOT increase the prompt length beyond 200 tokens
- **6f** — Document the final accuracy score and which queries failed in `tests/router_accuracy.md` — this is your proof the router works

---

## Task 7 — Query Execution Engine

**Goal:** Connect the router output to the index queries and produce the full TraceResult object.

*Depends on: 4c (graph_trace), 5d (vector_search), 6b (SLM router) — all must be working individually*

- **7a** — Write `engine/executor.py`:
  - Import `graph_trace`, `vector_search`, `RouterDecision`
  - `execute(conn, embedder, decision: RouterDecision) -> dict`:
    - If `decision.tool == "vector"`: call `vector_search`, skip graph trace
    - If `decision.tool == "graph"`: call `vector_search(top_k=1)` to find seed file, then call `graph_trace` on that file
    - If `decision.tool == "hybrid"`: call `vector_search(top_k=10)`, take top result as seed, call `graph_trace` on seed
    - Handle `no_match` case: if `vector_search` returns empty list, return early with `no_match=True`
    - Assemble the full TraceResult dict as specified in spec F4.2
    - Record `execution_ms` using `time.time()` before and after
- **7b** — Write edge case handling in `executor.py` (spec F4.3):
  - `no_match=True` when vector search returns nothing above similarity threshold
  - `depth_capped=True` propagated from `graph_trace` result
  - Empty `dependents`/`dependencies` arrays when seed file has no internal edges — never return null, always return `[]`
  - `routed_by` from the RouterDecision passes through unchanged into the TraceResult
- **7c** — Write `tests/test_executor.py`:
  - Use the already-built index from Task 5f (fastapi repo)
  - Test all three execution paths (graph, vector, hybrid) with known queries
  - Assert TraceResult structure is always complete — no missing keys
  - Assert `no_match` path returns correct shape with empty lists
  - Assert `depth_capped` triggers on a highly-connected seed node

---

## Task 8 — FastAPI Backend

**Goal:** Wrap everything in a REST API. All endpoints wired, env-aware, query history persisted.

*Depends on: 7a (executor ready), 4a (db ready), 5a (embedder ready), 6b (router ready)*

- **8a** — Write `api/main.py` skeleton:
  - Create FastAPI app instance
  - Load config from `config.py` (Task 1h)
  - On startup: call `init_db`, load embedder, open SQLite connection, ping Ollama
  - CORS middleware configured based on `ENV` variable (dev = localhost:5173, prod = subnet)
  - If `ENV=prod` and `FRONTEND_STATIC_DIR` is set: mount static files at `/`
- **8b** — Implement `POST /ingest` endpoint:
  - Validate `repo_path` exists on disk — return `repo_not_found` error if not
  - Run `parser/ingest.py` logic inline (import the functions, don't shell out)
  - Run `indexer/build.py` logic inline
  - Return ingest summary JSON (files_parsed, files_failed, symbols_indexed, duration_ms)
- **8c** — Implement `POST /query` endpoint:
  - Call `router/slm_router.py` → get RouterDecision
  - Call `engine/executor.py` → get TraceResult
  - Write to `query_history` table in SQLite (query, tool_used, routed_by, seed_file, result_json, execution_ms)
  - Return TraceResult as JSON response
- **8d** — Implement `GET /status` endpoint:
  - Check if DB file exists and has at least one node (index_loaded)
  - Ping Ollama API — set `ollama_reachable` true/false
  - Read current repo path from a stored config in SQLite or a simple text file
  - Read current process memory via `psutil` (`pip install psutil`)
  - Return full status JSON as per spec F5.2
- **8e** — Implement `GET /files` endpoint:
  - Query `nodes` table, return file path + language + count of functions/classes/exports for each
- **8f** — Implement `GET /history` endpoint:
  - Query `query_history` table, return last 20 rows ordered by `created_at DESC`
  - Return only summary fields (not full `result_json` blob) — frontend fetches details from stored state
- **8g** — Write standardized error responses for all common error codes in spec F5.5: `repo_not_found`, `index_not_built`, `ollama_unreachable`, `parse_failed`, `no_results`
- **8h** — Manual end-to-end test: start the API with `uvicorn api.main:app --reload`, use `curl` or Postman to hit all 5 endpoints, verify responses match the spec shapes exactly

---

## Task 9 — Frontend Dashboard

**Goal:** Build the React single-page app with all four panels. Dev server talking to local FastAPI.

*Depends on: 8h (all API endpoints confirmed working)*

- **9a** — Scaffold the React project inside `frontend/`:
  ```bash
  cd frontend
  npm create vite@latest . -- --template react
  npm install
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```
  Configure Tailwind in `tailwind.config.js` to scan `./src/**/*.{js,jsx}`
- **9b** — Create `frontend/src/config.js`:
  ```javascript
  const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
  export default API_BASE;
  ```
- **9c** — Write `frontend/src/api.js` — all API call functions in one place:
  - `ingestRepo(repoPath)` → POST /ingest
  - `submitQuery(query)` → POST /query
  - `getStatus()` → GET /status
  - `getFiles()` → GET /files
  - `getHistory()` → GET /history
  - All use `fetch`, all return parsed JSON, all throw on non-200
- **9d** — Build the Header Bar component:
  - App name on left
  - Environment badge (DEV yellow / PROD green) — read from status response `env` field
  - RAM usage display — updated every 5s via polling `getStatus()`
  - Ollama status dot — green/red from `ollama_reachable`
- **9e** — Build the Query Input Bar component:
  - Fixed to bottom of viewport
  - Text input + "Ask" button
  - `onSubmit` sets loading state → calls `submitQuery` → clears input on response
  - Disabled + spinner while loading
- **9f** — Build the Trace Output Panel component:
  - Accepts a `TraceResult` object as prop
  - Renders: seed symbol + file path at top
  - Dependents section: grouped by hop number, each file as a row
  - Dependencies section: same
  - Symbol matches section: name + kind badge + similarity score
  - Footer: routing metadata (routed_by, tool_used, execution_ms)
  - Empty state when no result yet
  - No-match state when `no_match=true`
- **9g** — Build the Query History Sidebar component:
  - Fetches `getHistory()` on mount
  - Re-fetches after each new query
  - Each history item shows truncated query + tool badge
  - Clicking an item: loads that item's stored `result_json` into the trace panel (no re-query)
- **9h** — Build the Ingest Panel component (collapsible):
  - Text input for repo path
  - "Ingest" button → calls `ingestRepo()` → shows result summary on success
  - Loading state during ingest (can take 20+ seconds, show spinner + message)
  - On success: refresh status bar (repo path updates)
- **9i** — Wire all components together in `frontend/src/App.jsx`:
  - Layout: header bar at top, sidebar + trace panel in middle, query input at bottom
  - Global state: `currentTrace` (null | TraceResult), `isLoading` (bool), `history` (array)
  - Ingest panel shown collapsed by default, expandable via toggle
- **9j** — End-to-end browser test: start Vite dev server (`npm run dev`), open `localhost:5173`, run an ingest, run 3 queries, verify trace renders correctly for all three tool types (graph, vector, hybrid)

---

## Task 10 — Integration & Dev Validation

**Goal:** Run the full stack end-to-end on dev, fix any integration issues, hit all performance targets.

*Depends on: 8h (API working), 9j (frontend working)*

- **10a** — Full pipeline test on `fastapi/fastapi` repo:
  - Ingest via dashboard UI
  - Run the 5 spec test queries
  - Verify: correct tool routing, correct seed file identified, plausible dependents/dependencies
  - Verify: response time under 500ms for all queries
- **10b** — Full pipeline test on `vercel/next.js` (src/ only):
  - Repeat above — TypeScript parser getting a real workout
  - Verify: exported component names appear in symbol matches
  - Verify: import relationships between files show in graph trace
- **10c** — Fallback path test:
  - Send a query that produces malformed JSON from the model (try single-character queries like "a")
  - Verify: fallback triggers, `routed_by: "fallback"` in response, dashboard shows "Fallback ⚠" indicator
  - Verify: result still renders correctly despite fallback
- **10d** — No-match path test:
  - Query for something that definitely doesn't exist in the indexed repo: `"find the blockchain consensus module"`
  - Verify: `no_match: true` in response, dashboard shows appropriate empty state message
- **10e** — Depth cap test:
  - Index a repo with high connectivity, query a central file like `app.py` or `index.ts`
  - Verify: `depth_capped: true` when appropriate, trace still renders without crashing
- **10f** — Fix any bugs found in 10a–10e before starting Task 11

---

## Task 11 — Jetson Deployment

**Goal:** Transfer the validated stack to Jetson, get it running on the local network, hit prod performance targets.

*Depends on: 1j (sqlite-vss ARM64 already validated), 10f (full dev stack validated)*

- **11a** — Prepare the Jetson (internet still connected):
  - Install Ollama ARM64 binary
  - Pull `llama3.2:1b`: `ollama pull llama3.2:1b`
  - Install Python deps: `pip install fastapi uvicorn sentence-transformers tree-sitter tree-sitter-languages python-dotenv psutil httpx --break-system-packages`
  - Run the embedder once to trigger `all-MiniLM-L6-v2` download and cache it locally
  - Confirm Ollama works: `ollama run llama3.2:1b "respond with the word ready"` → confirm it responds
- **11b** — Configure Ollama for 4GB memory (spec F7.3):
  - Edit `/etc/systemd/system/ollama.service`
  - Add environment variables: `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_GPU=999`, `OLLAMA_FLASH_ATTENTION=1`
  - `sudo systemctl daemon-reload && sudo systemctl restart ollama`
  - Verify model still loads after restart
- **11c** — Deploy project files to Jetson:
  - `rsync -av --exclude='index/' --exclude='__pycache__/' --exclude='.git/' ./ user@jetson:/opt/codegenome/`
  - Copy `.env.prod` to `/opt/codegenome/.env`
  - Update `VSS_EXTENSION_PATH` in `.env` to point to the built `vss0.so` from Task 1j
- **11d** — Build and deploy frontend static files:
  - On dev machine: `cd frontend && VITE_API_URL="" npm run build`
  - Transfer: `scp -r frontend/dist/ user@jetson:/opt/codegenome/frontend/dist/`
- **11e** — Set static IP on Jetson (spec F7.5):
  - `sudo nmcli con mod "Wired connection 1" ipv4.addresses 192.168.1.100/24`
  - `sudo nmcli con mod "Wired connection 1" ipv4.method manual`
  - `sudo nmcli con up "Wired connection 1"`
- **11f** — Create and enable systemd service for FastAPI (spec F7.4):
  - Write service file at `/etc/systemd/system/codegenome.service`
  - `sudo systemctl enable codegenome && sudo systemctl start codegenome`
  - Watch logs: `sudo journalctl -u codegenome -f` — confirm startup completes without errors
- **11g** — Set up memory watchdog (spec F7.7):
  - Write `watchdog.sh` to `/opt/codegenome/watchdog.sh`, make executable
  - Add crontab entry: `*/2 * * * * /opt/codegenome/watchdog.sh`
- **11h** — End-to-end prod test from a second device on the same network:
  - Open `http://192.168.1.100:8000` in browser on laptop
  - Ingest the `fastapi/fastapi` source (copy it to Jetson at `/mnt/repos/fastapi`)
  - Run all 5 spec test queries
  - Verify: response time under 3 seconds for all queries
  - Verify: RAM stays under 3.2GB throughout (check dashboard status bar)
- **11i** — Cold boot test:
  - Power off Jetson completely
  - Power on, start timer
  - Open dashboard in browser when ready
  - Record time — must be under 90 seconds
- **11j** — Run full demo day checklist from spec F7.8:
  - [ ] Cold boot under 90s ✓ (from 11i)
  - [ ] Ingest demo repo cleanly ✓
  - [ ] All 5 test queries correct ✓
  - [ ] RAM under 3.2GB ✓
  - [ ] Fallback path works ✓
  - [ ] Second device can connect ✓
  - [ ] Backup `codegenome.db` file saved somewhere safe ✓

---

## Task 12 — Polish & Demo Prep

**Goal:** Clean up rough edges, prepare the demo script, make the tool presentable.

*Depends on: 11j (all prod checks passed)*

- **12a** — Review all error states in the dashboard — make sure every error code from the API shows a human-readable message, not a raw JSON blob
- **12b** — Add loading skeleton/shimmer to the Trace Output Panel so the UI doesn't flash blank while waiting for a response
- **12c** — Write `README.md` with: what the project does, how to run it on dev, how to deploy to Jetson, the 5 test queries, and the router accuracy score
- **12d** — Prepare the demo repo: pick one well-known open-source repo (fastapi/fastapi recommended), pre-index it, save the `codegenome.db` as a backup file
- **12e** — Write and rehearse the demo script:
  - Open the dashboard — show the status bar (Jetson, PROD, RAM, Ollama green)
  - Point at the indexed repo name
  - Run query 1: "Where does this app handle authentication?" — walk through the trace
  - Run query 2: "What breaks if I change the routing module?" — show dependents
  - Run query 3: "Find the database session handler" — pure vector path
  - Show the query history sidebar — replay a previous query
  - Deliberately trigger fallback — show the ⚠ indicator — explain why it's a feature not a bug
- **12f** — Rehearse the demo twice end-to-end on the Jetson with the actual device, not on dev machine

---

## Task Summary Table

| Task | Description | Week | Depends On |
|---|---|---|---|
| T1 | Project setup & environment | 1 | — |
| T2 | Python AST parser | 1–2 | T1 |
| T3 | TypeScript AST parser + ingest CLI | 2 | T2 |
| T4 | SQLite graph index | 3 | T3 |
| T5 | SQLite vector index | 3–4 | T4 |
| T6 | SLM router | 2–3 | T1 |
| T7 | Query execution engine | 4 | T4, T5, T6 |
| T8 | FastAPI backend | 5 | T7 |
| T9 | Frontend dashboard | 6 | T8 |
| T10 | Dev integration & validation | 6–7 | T8, T9 |
| T11 | Jetson deployment | 7–8 | T1j, T10 |
| T12 | Polish & demo prep | 8 | T11 |

---

## Task Dependency Graph

```
T1 (Project Setup)
│
├──────────────────────────────┐
│                              │
▼                              ▼
T2 (Python Parser)         T6 (SLM Router) ←── requires Ollama from T1
│
▼
T3 (TypeScript Parser + Ingest CLI)
│
▼
T4 (Graph Index)
│
├──────────────────────────────┐
│                              │
▼                              ▼
T5 (Vector Index)          [T6 completes independently]
│                              │
└──────────────┬───────────────┘
               │
               ▼
           T7 (Execution Engine)
               │
               ▼
           T8 (FastAPI Backend)
               │
               ▼
           T9 (Frontend)
               │
               ▼
           T10 (Dev Integration)
               │
               ▼
           T11 (Jetson Deploy) ←── also requires T1j (sqlite-vss ARM64 build)
               │
               ▼
           T12 (Polish & Demo)


Early parallel path (do not skip):
T1 ──► T1j (Jetson sqlite-vss build) ──────────────────────► T11
```

### Critical Path

The sequence that directly determines your demo date:

```
T1 → T2 → T3 → T4 → T5 → T7 → T8 → T9 → T10 → T11 → T12
```

T6 (SLM Router) can be built in parallel with T2–T3 since it only needs Ollama running (T1).
T1j (Jetson sqlite-vss build) must happen in Week 1 alongside T1, not at the end.

### Where Things Can Go Wrong (Risk Nodes)

```
T1j ── HIGH RISK ── sqlite-vss ARM64 build failure blocks T11 entirely
T5  ── MEDIUM RISK ── sqlite-vss on dev might have issues; vector quality may need tuning  
T6  ── MEDIUM RISK ── router accuracy gate (17/20) may need prompt iteration
T11 ── HIGH RISK ── memory pressure, cold boot time, ARM64 quirks
```

If T1j fails or takes more than a day to resolve, the fallback is to replace `sqlite-vss` with
a pure Python brute-force vector search (cosine similarity over numpy arrays) for the demo. It's
slower but it runs anywhere. Keep this option in mind.
```

---

*End of Task List*
