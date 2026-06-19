# CodeGenome-Edge — Test Queries Guide

To experience the full capabilities of **CodeGenome-Edge**, you can index its own codebase (which is a mixed Python and React/TypeScript repository). 

This guide details a set of test queries designed to show off the system's AST indexing, SLM intent classification, graph traversal, semantic search, and streaming explanations.

---

## Preparation: Ingesting CodeGenome-Edge

1.  Open the web dashboard at `http://localhost:5173`.
2.  Expand the **Ingest Panel** at the top.
3.  Enter the absolute path of this repository: `d:/repo/Edge_minds`.
4.  Click **Ingest** and wait for the status bar to show the successfully indexed nodes and symbols.

---

## 1. Vector Search (Semantic Lookup Queries)

*These queries test the system's ability to map natural language concepts to tree-sitter symbol blueprints via the embedding index.*

### Test Query A: *"Find the Python parsing functions"*
*   **Expected Tool**: `vector`
*   **Extracted Keywords**: `["python", "parsing", "functions"]`
*   **Expected Results**:
    *   **Seed / Match 1**: `parse_python_file` in `parser/python_parser.py` (Kind: `function`)
    *   **Match 2**: `ingest_repository` or similar in `parser/ingest.py`
*   **Why this is a good test**: It validates that `sentence-transformers` successfully maps the concept "python parsing" to the exact parsed tree-sitter function `parse_python_file`.

### Test Query B: *"Where is the sqlite load extension configured?"*
*   **Expected Tool**: `vector`
*   **Extracted Keywords**: `["sqlite", "load", "extension", "configured"]`
*   **Expected Results**:
    *   **Seed / Match 1**: `get_connection` in `indexer/db.py` (Kind: `function`)
    *   **Match 2**: `init_db` in `indexer/db.py`
*   **Why this is a good test**: It showcases semantic matching for a specific feature query. Even if the words "configured" or "sqlite load extension" are not exact, it matches the context of loading sqlite extensions in the database code.

---

## 2. Graph Search (Dependency & Import Tracking)

*These queries test the BFS query engine's ability to trace import relationships up to 3 hops.*

### Test Query C: *"What files import the config module?"*
*   **Expected Tool**: `graph`
*   **Extracted Keywords**: `["files", "import", "config", "module"]`
*   **Expected Results**:
    *   **Seed Node**: `api/config.py`
    *   **Upstream Dependents (Hop 1)**: `api/main.py`, `router/slm_router.py`
*   **Why this is a good test**: It verifies that the import parser mapped the custom python package imports `from api.config import ...` to structural graph edges and correctly resolves them upstream.

### Test Query D: *"What files import the file scanner?"*
*   **Expected Tool**: `graph`
*   **Extracted Keywords**: `["files", "import", "file", "scanner"]`
*   **Expected Results**:
    *   **Seed Node**: `parser/file_scanner.py`
    *   **Upstream Dependents (Hop 1)**: `parser/ingest.py`
    *   **Upstream Dependents (Hop 2)**: `api/main.py`
*   **Why this is a good test**: Demonstrates a **multi-hop** dependent query. `file_scanner` is imported by `ingest.py` which is in turn imported by `main.py`. The graph output should visually group this by Hop 1 and Hop 2.

---

## 3. Hybrid Search (Semantic Locating + Change Impact)

*These queries use vector search to locate a target symbol or module, and then automatically trigger a BFS trace to determine its dependencies and blast radius.*

### Test Query E: *"What breaks if I change the TS parser?"*
*   **Expected Tool**: `hybrid`
*   **Extracted Keywords**: `["breaks", "change", "TS", "parser"]`
*   **Expected Results**:
    *   **Seed Node**: `parser/typescript_parser.py` (located via vector lookup for "TS parser")
    *   **Upstream Dependents (Hop 1)**: `parser/ingest.py`
    *   **Upstream Dependents (Hop 2)**: `api/main.py`
*   **Why this is a good test**: Shows the "blast radius" query. Changing `typescript_parser.py` directly impacts the `ingest.py` utility, and transitively propagates up to the main API entrypoint.

### Test Query F: *"Where is the vector_search function located and who depends on it?"*
*   **Expected Tool**: `hybrid`
*   **Extracted Keywords**: `["vector_search", "function", "located", "depends"]`
*   **Expected Results**:
    *   **Seed Node**: `vector_search` in `indexer/vector_query.py`
    *   **Upstream Dependents (Hop 1)**: `engine/executor.py`
    *   **Upstream Dependents (Hop 2)**: `api/main.py`
*   **Why this is a good test**: It highlights a hybrid intent. It finds a specific symbol name, anchors it, and displays both its file matches and the files importing its source container.

---

## 4. Layer-Filtered Queries

*These queries demonstrate the API's regex classifier that filters search results based on code architecture layers (`frontend` vs `backend`).*

### Test Query G: *"Find the main handler in the backend"*
*   **Expected Tool**: `vector`
*   **Detected Layer Filter**: `backend`
*   **Expected Results**: Focuses on symbols located in `api/main.py` or other backend packages, ignoring components and scripts.

### Test Query H: *"Where is the header component in the frontend?"*
*   **Expected Tool**: `vector`
*   **Detected Layer Filter**: `frontend`
*   **Expected Results**: Displays `Header.jsx` or similar in `frontend/src/components/Header.jsx`.

---

## 5. Fallback Routing & Parsing Test

*These queries verify the robustness of the system when natural language processing gets interrupted or is given sparse input.*

### Test Query I: *"API"*
*   **Expected Tool**: `hybrid` (Fallback default)
*   **Routed By**: `fallback` (indicated on the UI by a `Fallback ⚠` badge)
*   **Extracted Keywords**: `["api"]`
*   **Expected Results**: Will execute a vector and graph search for files/symbols matching the keyword `api`.
*   **Why this is a good test**: Demonstrates that the backend handles sparse, one-word queries gracefully by bypassing SLM timeouts/failures and using regex keyword extraction.
