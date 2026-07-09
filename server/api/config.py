import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configuration constants
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
# Number of model layers to offload to GPU.
# -1 = auto-detect (Ollama assigns all available layers to the GPU, recommended for Jetson)
#  0 = CPU-only (disables GPU — avoid on Jetson)
# >0 = explicit layer count (use if you want to cap GPU memory usage)
OLLAMA_NUM_GPU: int = int(os.getenv("OLLAMA_NUM_GPU", "-1"))
DB_PATH: str = os.getenv("DB_PATH", "./index/codegenome.db")
MANIFEST_PATH: str = os.getenv("MANIFEST_PATH", "./index/manifest.json")
API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
FRONTEND_STATIC_DIR: str = os.getenv("FRONTEND_STATIC_DIR", "")
ENV: str = os.getenv("ENV", "dev")

# Print configuration summary on startup
print(f"--- CodeGenome-Edge Config Loaded ---")
print(f"ENV: {ENV}")
print(f"OLLAMA_BASE_URL: {OLLAMA_BASE_URL}")
print(f"OLLAMA_MODEL: {OLLAMA_MODEL}")
print(f"OLLAMA_NUM_GPU: {OLLAMA_NUM_GPU} ({'auto' if OLLAMA_NUM_GPU == -1 else 'CPU-only' if OLLAMA_NUM_GPU == 0 else f'{OLLAMA_NUM_GPU} layers'})")
print(f"DB_PATH: {DB_PATH}")
print(f"MANIFEST_PATH: {MANIFEST_PATH}")
print(f"API: {API_HOST}:{API_PORT}")
print(f"-------------------------------------")

