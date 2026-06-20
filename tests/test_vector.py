import unittest
import sqlite3
import json

from server.indexer.db import init_db
from server.indexer.vector_query import vector_search
from server.indexer import embedder

class TestVectorQueries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We can load the embedder once for all tests to speed it up
        cls.embedder = embedder
        
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        
        # Setup schema manually
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            language TEXT NOT NULL,
            layer TEXT DEFAULT 'unknown',
            embedding TEXT,
            purpose TEXT,
            trigger TEXT,
            key_behavior TEXT
        )
        """)
        
        # Populate with some mock symbols and compute their actual embeddings
        # so the cosine similarity test is realistic!
        mock_symbols = [
            ("src/auth/middleware.py", "verify_token", "function", "python", "backend"),
            ("src/auth/middleware.py", "AuthMiddleware", "class", "python", "backend"),
            ("src/routes/user.py", "get_user_profile", "function", "python", "backend"),
            ("src/db/session.py", "get_db_session", "function", "python", "backend")
        ]
        
        names = [item[1] for item in mock_symbols]
        vectors = self.embedder.embed_batch(names)
        
        for (file_path, name, kind, lang, layer), vector in zip(mock_symbols, vectors):
            self.cursor.execute(
                """
                INSERT INTO symbols (file_path, name, kind, language, layer, embedding)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_path, name, kind, lang, layer, json.dumps(vector))
            )
        self.conn.commit()
        
    def tearDown(self):
        self.conn.close()
        
    def test_semantic_match_exact(self):
        # Searching for "verify token" should return verify_token as top match
        res = vector_search(self.conn, self.embedder, ["verify", "token"], top_k=5, has_vss=False)
        self.assertTrue(len(res) > 0)
        self.assertEqual(res[0]["name"], "verify_token")
        self.assertTrue(res[0]["similarity"] >= 0.70)
        
    def test_semantic_match_concept(self):
        # Searching for "database connection session" should return get_db_session
        res = vector_search(self.conn, self.embedder, ["database", "connection"], top_k=5, has_vss=False)
        self.assertTrue(len(res) > 0)
        self.assertEqual(res[0]["name"], "get_db_session")
        self.assertTrue(res[0]["similarity"] >= 0.38)
        
    def test_similarity_cutoff(self):
        # Searching for completely unrelated query like "blockchain consensus block"
        res = vector_search(self.conn, self.embedder, ["blockchain", "consensus"], top_k=5, has_vss=False)
        # Should not match any symbols with similarity >= 0.35
        self.assertEqual(len(res), 0)

if __name__ == "__main__":
    unittest.main()
