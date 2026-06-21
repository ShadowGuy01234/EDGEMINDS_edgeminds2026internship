# CodeGenome-Edge

CodeGenome-Edge is a local-only, offline-first codebase intelligence tool designed to run completely offline, even on resource-constrained edge hardware like the NVIDIA Jetson Orin Nano. It allows engineers to query the structure of a codebase using natural language and maps dependencies, imports, and symbols via a hybrid local graph + vector indexing model.

---

## Key Features

1.  **AST-Based Blueprints**: Lightweight parser utilizing `tree-sitter` to parse Python and TypeScript structure, extracting imports, exports, functions, classes, and lines metadata.
2.  **Dual-Index Store**: A local SQLite database mapping files as a structural import graph alongside semantic symbol definitions.
3.  **Local SLM Query Routing**: Uses a local Ollama instance running `llama3.2:1b` to extract search intent, parameters, and keywords.
4.  **Deterministic Search Engine**: Breadth-First Search (BFS) graph execution up to 3 hops (upstream dependents and downstream dependencies) combined with vector search.
5.  **Graph-Enriched Explanations**: Automatically extracts function signatures and docstrings to inject callers and callees as context-augmented RAG data for on-demand symbol explanations.
6.  **"Blast Radius" Impact Analysis**: Traces 3-hop dependent files via BFS and runs SLM summarization to determine modification risks and testing scenarios.
7.  **Interactive Web Dashboard**: React frontend dashboard displaying file traces, dynamic tabbed symbol panels (Explanation / Blast Radius), status metrics, and memory footprints.

---

## Repository Structure

```
codegenome-edge/
├── api/             # FastAPI REST endpoints & configuration
├── engine/          # Query execution engine coordinating searches
├── indexer/         # SQLite Dual-Index graph & vector builder and query layer
├── parser/          # AST parse scanner for Python and TypeScript
├── router/          # Local SLM query router & stopword keywords fallback
├── frontend/        # React single page application dashboard
├── docs/            # Specifications, tasks list, and detailed guides
│   ├── architecture.md    # Detailed architecture & code-mapping guide
│   ├── test_queries.md    # Guide with test queries that yield good results
│   ├── CodeGenome-Edge-Spec.md
│   └── CodeGenome-Edge-Tasks.md
├── tests/           # Full pytest validation suite
├── requirements.txt # Python dependencies
└── README.md        # Quickstart and overview
```

*   For a detailed file-by-file breakdown, sequence diagrams, and database schemas, please refer to the **[Technical Architecture & Codebase Guide](docs/architecture.md)**.
*   For sample search queries showcasing vector, graph, hybrid, layer-filtered, and fallback search modes, see the **[Test Queries Guide](docs/test_queries.md)**.

---

## Startup & Troubleshooting Guide

Follow these instructions to configure, run, and troubleshoot the CodeGenome-Edge stack.

### 1. Prerequisites & Dependencies

#### Ollama & SLM Model
Make sure you have [Ollama](https://ollama.com/) installed and running locally, then pull the required model:
```bash
ollama pull llama3.2:1b
```
Ensure Ollama is running in the background and is reachable by visiting `http://localhost:11434` in your browser.

#### Python Dependencies
Install all package dependencies at the repository root:
```bash
pip install -r requirements.txt
```

#### Node.js (for Frontend Development)
Ensure you have Node.js (v18+) and npm installed to run the local Vite frontend development server.

---

### 2. Configuration Settings
Create a `.env` file at the root of the repository (`d:\repo\Edge_minds\.env`) and configure the settings:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
DB_PATH=./index/codegenome.db
MANIFEST_PATH=./index/manifest.json
API_HOST=127.0.0.1
API_PORT=8000
FRONTEND_STATIC_DIR=          # Leave empty in development
ENV=dev
```

---

### 3. Starting the FastAPI Backend API

> [!IMPORTANT]
> **Working Directory Warning:** You **MUST** run the backend server from the **repository root directory** (`d:\repo\Edge_minds`). 
> If you run `python -m uvicorn api.main:app`, python will fail to resolve the package and throw: `ModuleNotFoundError: No module named 'api'`.

#### Correct Start Command (From Repository Root)
Run the FastAPI backend using `python -m uvicorn`:
```bash
# Verify you are at d:\repo\Edge_minds
python -m uvicorn server.api.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Verifying Backend Startup
Open your browser and navigate to:
*   **System Status**: `http://127.0.0.1:8000/status` (Check if `ollama_reachable` is `true`).
*   **Swagger API Docs**: `http://127.0.0.1:8000/docs` (Interactive API playground).

---

### 4. Starting the Frontend Dashboard

From another terminal, navigate to the `frontend/` directory, install npm packages, and start the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. The dashboard status bar should show `DEV` (yellow), a green dot for Ollama connectivity, and active process RAM metrics.

---

### 5. Running Ingestion
To query a codebase, you must first ingest it to parse the AST elements and build the database:
1.  Open the web dashboard at `http://localhost:5173`.
2.  Expand the **Ingest Panel** at the top.
3.  Enter the absolute path of the target codebase you want to analyze (e.g. `d:/repo/Edge_minds`).
4.  Click **Ingest**. Once complete, the status bar will show the counts of parsed files and symbols.

---

### 6. Common Issues & Troubleshooting

#### 1. `ModuleNotFoundError: No module named 'api'` or `ModuleNotFoundError: No module named 'server'`
*   **Cause**: You specified the wrong module name or ran the `uvicorn` command inside the wrong directory.
*   **Fix**: Return to the repository root directory (`d:\repo\Edge_minds`) and run:
    ```bash
    python -m uvicorn server.api.main:app --host 127.0.0.1 --port 8000 --reload
    ```

#### 2. `ollama_reachable: false` or Warning on Startup
*   **Cause**: The Ollama background daemon is not running, or it's listening on a different port.
*   **Fix**: Start the Ollama application. Verify the configuration by running `curl http://localhost:11434/api/tags` in your terminal and ensure `llama3.2:1b` is listed.

#### 3. `index_not_built` (HTTP 400 when submitting queries)
*   **Cause**: You submitted a query before ingesting any repository.
*   **Fix**: Use the dashboard Ingest Panel or hit `POST /ingest` with the target `repo_path` first to build the SQLite index.

#### 4. `sqlite-vss` Load Failures
*   **Cause**: Missing or incompatible compiled C-extensions for vector search (common on ARM64 and Windows).
*   **Fix**: No action required. CodeGenome-Edge detects the absence of `sqlite-vss` and falls back automatically to a Numpy/pure-math Python cosine similarity query loop.

---

### 7. Verification Tests

To run the automated validation tests, execute `pytest` from the root directory:
```bash
python -m pytest
```
Tests cover AST parsing, layer classification, SQLite database queries, SLM routing accuracy checks, search execution, and REST endpoints.

