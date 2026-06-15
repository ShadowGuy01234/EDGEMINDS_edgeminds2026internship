import unittest
import sqlite3
import json
import os
import tempfile

from parser.layer_classifier import classify_layer
from indexer.vector_query import vector_search
from indexer.db import init_db
from indexer.vector_builder import insert_symbols
from indexer.graph_builder import insert_nodes

class MockEmbedder:
    def embed(self, text):
        return [0.1] * 384
    def embed_batch(self, texts):
        return [[0.1] * 384 for _ in texts]

class TestLayerAwareness(unittest.TestCase):
    def test_layer_classification(self):
        self.assertEqual(classify_layer("backend/src/middleware/auth.js"), "backend")
        self.assertEqual(classify_layer("frontend/src/context/AuthContext.tsx"), "frontend")
        self.assertEqual(classify_layer("format.py"), "backend") # fallback python
        self.assertEqual(classify_layer("format.tsx"), "frontend") # fallback jsx/tsx
        self.assertEqual(classify_layer("tests/test_api.py"), "test")
        self.assertEqual(classify_layer("shared/types.ts"), "shared")
        
    def test_vector_search_layer_filter(self):
        db_fd, db_path = tempfile.mkstemp()
        try:
            conn = init_db(db_path)
            # Create mock blueprints
            blueprints = [
                {
                    "file_path": "backend/src/middleware/auth.js",
                    "language": "javascript",
                    "functions": ["authenticate"],
                    "classes": [],
                    "exports": ["authenticate"],
                    "layer": "backend"
                },
                {
                    "file_path": "frontend/src/hooks/useAuth.ts",
                    "language": "typescript",
                    "functions": ["useAuth"],
                    "classes": [],
                    "exports": ["useAuth"],
                    "layer": "frontend"
                },
                {
                    "file_path": "shared/utils.ts",
                    "language": "typescript",
                    "functions": ["formatDate"],
                    "classes": [],
                    "exports": ["formatDate"],
                    "layer": "shared"
                }
            ]
            
            embedder = MockEmbedder()
            
            # Insert nodes and symbols
            insert_nodes(conn, blueprints)
            insert_symbols(conn, blueprints, embedder, has_vss=False)
            
            # Query without filter - should return all auth symbols
            res_all = vector_search(conn, embedder, ["auth"], top_k=10, has_vss=False)
            names_all = [r["name"] for r in res_all]
            self.assertIn("authenticate", names_all)
            self.assertIn("useAuth", names_all)
            
            # Query with backend filter
            res_backend = vector_search(conn, embedder, ["auth"], top_k=10, has_vss=False, layer_filter="backend")
            names_backend = [r["name"] for r in res_backend]
            self.assertIn("authenticate", names_backend)
            self.assertNotIn("useAuth", names_backend)
            
            # Query with frontend filter
            res_frontend = vector_search(conn, embedder, ["auth"], top_k=10, has_vss=False, layer_filter="frontend")
            names_frontend = [r["name"] for r in res_frontend]
            self.assertNotIn("authenticate", names_frontend)
            self.assertIn("useAuth", names_frontend)
            
            # Shared should be included in both filters
            res_shared_b = vector_search(conn, embedder, ["format"], top_k=10, has_vss=False, layer_filter="backend")
            names_shared_b = [r["name"] for r in res_shared_b]
            self.assertIn("formatDate", names_shared_b)
            
            res_shared_f = vector_search(conn, embedder, ["format"], top_k=10, has_vss=False, layer_filter="frontend")
            names_shared_f = [r["name"] for r in res_shared_f]
            self.assertIn("formatDate", names_shared_f)
            
        finally:
            conn.close()
            os.close(db_fd)
            try:
                os.remove(db_path)
            except Exception:
                pass

if __name__ == "__main__":
    unittest.main()
