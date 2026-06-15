from indexer import embedder
from indexer.vector_query import calculate_cosine_similarity
v1 = embedder.embed("database connection")
v2 = embedder.embed("get_db_session")
print("Similarity:", calculate_cosine_similarity(v1, v2))
