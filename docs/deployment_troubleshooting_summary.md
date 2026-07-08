# CodeGenome-Edge: NVIDIA Jetson Deployment & Troubleshooting Summary

This document summarizes the troubleshooting steps, root causes, and solutions implemented while deploying **CodeGenome-Edge** on the NVIDIA Cloud Lab (JetPack 6.x environment).

---

## 1. Port Forwarding & ngrok Tunneling
* **Problem**: Need to expose port `8000` to the internet using a single browser SSH terminal.
* **Solution**: 
  1. Updated the deployment guide with active download links for the Linux ARM64 ngrok package:
     ```bash
     wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz
     tar -xvzf ngrok-v3-stable-linux-arm64.tgz
     ```
  2. Started ngrok as a daemon in the background to keep the terminal free:
     ```bash
     ~/ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
     ```

---

## 2. Ollama CUDA Out of Memory (OOM) Errors
* **Problem**: Attempting to load the Llama 3.2 1B model crashed Ollama with `cudaMalloc failed: out of memory`. This occurred because the PyTorch backend had already allocated the shared GPU memory for the embeddings model.
* **Solution**: Configured Ollama to run entirely in CPU-only mode:
  ```bash
  kill -9 $(pgrep ollama)
  kill -9 $(pgrep llama)
  CUDA_VISIBLE_DEVICES="" OLLAMA_HOST="0.0.0.0" ollama serve > ~/ollama.log 2>&1 &
  ```
  Since Llama 3.2 1B is highly compact, it runs fast enough on the Jetson's ARM64 CPU cores while leaving the GPU free for embeddings.

---

## 3. Client Timeout Exceeded (500/Fallback Errors)
* **Problem**: The SLM router and explanation endpoints returned timeouts or fell back to keyword routing because CPU execution takes longer than GPU execution (routing took ~50.2s, which exceeded the default 15s/30s/50s limits).
* **Solution**: Increased all HTTP client timeouts to **180 seconds** (3 minutes) in both:
  * [main.py](file:///d:/repo/Edge_minds/server/api/main.py) (Explanation, Chat, and Impact endpoints)
  * [slm_router.py](file:///d:/repo/Edge_minds/server/router/slm_router.py) (Routing classification endpoint)

---

## 4. Ollama Load Timeout (`context canceled`)
* **Problem**: When loading the 1.3 GB `llama3.2:1b` model, Ollama aborted the load with `timed out waiting for llama-server to start: context canceled`. This occurs on slower cloud filesystems/network drives where reading 1.3 GB takes longer than Ollama's default startup window.
* **Solution**: Started Ollama with the load timeout environment variable set to 5 minutes:
  ```bash
  OLLAMA_LOAD_TIMEOUT=5m OLLAMA_HOST="0.0.0.0" ollama serve &
  ```

---

## 5. Host GPU VRAM Exhaustion in Shared Container Environments
* **Problem**: `cudaMalloc failed: out of memory` persisted even when no local container processes were using the GPU. In shared Cloud Lab environments (like AiProff.ai), other containers on the same physical Jetson host occupy the unified GPU VRAM, leaving less than 1.25 GB available.
* **Solution**: Partitioned resources to run entirely on the CPU:
  1. Hided the GPU from the Python FastAPI server to prevent PyTorch from initializing CUDA contexts:
     ```bash
     CUDA_VISIBLE_DEVICES="" python -m uvicorn server.api.main:app ...
     ```
  2. Forced PyTorch SentenceTransformer to use CPU exclusively in `server/indexer/embedder.py`:
     ```python
     _model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
     ```
  3. Ran Ollama in CPU-only mode to bypass the shared host GPU constraints:
     ```bash
     CUDA_VISIBLE_DEVICES="" OLLAMA_LOAD_TIMEOUT=5m OLLAMA_HOST="0.0.0.0" ollama serve &
     ```

