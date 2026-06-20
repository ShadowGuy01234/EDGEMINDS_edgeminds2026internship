# CodeGenome-Edge — Project Summary

Offline-first codebase intelligence tool running on edge hardware (NVIDIA Jetson).

## Currently Implemented

1. **AST Parsers** (`server/parser/`): Python and TypeScript scanners extracting imports, exports, functions, and classes while skipping implementation logic. Records precise 1-indexed source code line ranges (`start_line`, `end_line`) for all symbols.
2. **Dual-Index DB Store** (`server/indexer/`): SQLite database mapping code file imports (BFS up to 3 hops) alongside vector symbol embeddings (`all-MiniLM-L6-v2`). Automatically falls back to NumPy-based search if `sqlite-vss` is missing. Stores `start_line` and `end_line` metadata for each symbol.
3. **On-Demand Raw Slicer** (`server/retriever/raw_slicer.py`): Utility that reads codebase files and slices exact line ranges for specific symbols. If a symbol extends beyond 300 lines, it truncates the code to 300 lines and appends a `// ...truncated...` comment block.
4. **On-Demand SSE Streaming Endpoint** (`server/api/main.py`): A streaming POST endpoint `/symbol/explain` that takes a symbol request (file path, name, kind), queries symbol line ranges and language from the DB, extracts the source slice, and feeds it to local Ollama (`llama3.2:1b`) with a Markdown-focused RAG prompt. Responses are streamed chunk-by-chunk to the client using Server-Sent Events (SSE).
5. **Strict Prompt formatting**: The backend Ollama prompt strictly enforces standard ATX-style Markdown headers (`## Purpose`) and explicitly forbids Setext-style header underlining (`===` or `---`) to prevent visual glitches.
6. **Lightweight Markdown Sanitizer** (`frontend/src/components/TracePanel.jsx`): A client-side regex-based sanitizer function `sanitizeMarkdown()` that cleans up Setext header dashes and equal signs dynamically before rendering the stream chunk in the React UI.
7. **Interactive Click-to-Stream UI** (`frontend/`): Upgraded the Trace Panel matched symbols view. Clicking a match dynamically fetches, decodes, and streams symbol explanations token-by-token directly inside the search result list. Shows a "Generating..." indicator and has live pulse animations.
8. **SLM Intent Router** (`server/router/`): Local Ollama (`llama3.2:1b`) parsing query intent into `graph`, `vector`, or `hybrid` execution paths. Includes a stopword fallback parser (100% accuracy, 20/20 test queries).
9. **Execution Engine** (`server/engine/`): Combines vector and graph queries to return trace results, dependents, and symbol matches.
10. **FastAPI REST API** (`server/api/`): Core endpoints for `/ingest`, `/query`, `/status` (monitoring RAM/Ollama), `/files`, `/history`, and `/symbol/explain` (on-demand explanations). Ingestion runs instantly without pre-computing explanations.

## System Workflows

### 1. Ingestion & Indexing Pipeline
```
[Workspace Repo Path]
       │
       ▼ (1. Scans codebase & filters files >500KB or in ignored folders)
[server/parser/file_scanner.py]
       │
       ▼ (2. Parses Python / TS AST trees-sitter nodes; extracts line ranges and signatures)
[server/parser/python_parser.py] & [server/parser/typescript_parser.py]
       │
       ▼ (3. Tags files as frontend / backend / shared / test)
[server/parser/layer_classifier.py]
       │
       ▼ (4. Writes structured AST representation)
[index/manifest.json]
       │
       ▼ (5. Builds DB structures: nodes, imports edges, start/end lines, and symbol names)
[server/indexer/graph_builder.py]
       │
       ▼ (6. Batch-embeds symbol names via SentenceTransformers)
[server/indexer/vector_builder.py]
       │
       ▼
[index/codegenome.db] (Final database structure, ingestion complete instantly)
```

### 2. On-Demand Explanation Stream (Lazy RAG)
```
[Developer clicks on a Match in Trace Panel UI]
       │
       ▼ (1. Initiates POST /symbol/explain stream request)
[server/api/main.py] (FastAPI Endpoint)
       │
       ▼ (2. Queries start_line and end_line for symbol)
[index/codegenome.db]
       │
       ▼ (3. Extracts raw symbol code and bounds to 300 lines limit)
[server/retriever/raw_slicer.py]
       │
       ▼ (4. Formulates strict Markdown prompt; calls Ollama with stream=True)
[Ollama llama3.2:1b]
       │
       ▼ (5. SSE Stream yields chunks: data: {"chunk": "..."} )
[SSE text/event-stream Response]
       │
       ▼ (6. Client cleans Setext headers via regex sanitizer & appends tokens to layout block)
[TracePanel UI Pre-wrap Panel]
```

## Directory Cleanup

We removed all obsolete scripts, tests, and folders referencing the eager/removed explanation pipeline to keep the directory lean:
- **Removed Folders:**
  - `explain/` (contain old pre-computation prompt/pipeline logic)
  - `eval/` (contain old evaluation scripts and result CSVs)
- **Removed Files:**
  - `retriever/source_slicer.py` (replaced by raw_slicer)
  - `tests/test_explain_units.py` (obsolete unit tests matching eager pipeline)
  - `scripts/test_pipeline.py` (obsolete test script)
  - `scripts/test_prompt.py` (obsolete test script)
  - `scripts/diagnose_9534.py` (obsolete diagnostic script)
  - `server.log` (temporary local log file)

## Status & Validation

- **Ingestion**: Clean, builds SQLite schemas and vector embeddings instantly without eager pre-computation latency.
- **On-Demand Explanations**: Streamed dynamically via Server-Sent Events in standard Markdown (Purpose, Key Logic, Context) directly inside the Trace Panel.
- **Working Tree**: Clean, all code versioned and completed on branch `main`.
