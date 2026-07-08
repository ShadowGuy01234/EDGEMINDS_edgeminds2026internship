import time
from typing import List
from sentence_transformers import SentenceTransformer

# Singleton pattern for the embedding model to avoid loading it repeatedly
_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading SentenceTransformer model 'all-MiniLM-L6-v2' on device '{device}'...")
        start_time = time.time()
        _model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
        print(f"Model loaded in {time.time() - start_time:.2f} seconds.")
    return _model

def embed(text: str) -> List[float]:
    """
    Computes a 384-dimensional embedding for a single text query.
    """
    model = get_model()
    vector = model.encode(text, convert_to_numpy=True)
    return vector.tolist()

def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Computes 384-dimensional embeddings for a list of strings in a single batch.
    """
    if not texts:
        return []
    model = get_model()
    vectors = model.encode(texts, convert_to_numpy=True)
    return [vector.tolist() for vector in vectors]
