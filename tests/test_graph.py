import unittest
import sqlite3
import json

from server.indexer.db import init_db
from server.indexer.graph_query import graph_trace

class TestGraphQueries(unittest.TestCase):
    def setUp(self):
        # Initialize an in-memory SQLite DB
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        
        # Manually create tables for speed in testing
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            target_name TEXT NOT NULL,
            import_type TEXT NOT NULL
        )
        """)
        
        # Populate with a known mock dependency tree:
        # A depends on B and C.
        # B depends on D.
        # D depends on E.
        # F depends on A.
        mock_edges = [
            ("A", "B", "internal"),
            ("A", "C", "internal"),
            ("B", "D", "internal"),
            ("D", "E", "internal"),
            ("F", "A", "internal"),
            ("A", "external_lib", "external") # should be ignored by BFS
        ]
        self.cursor.executemany(
            "INSERT INTO edges (source_file, target_name, import_type) VALUES (?, ?, ?)",
            mock_edges
        )
        self.conn.commit()
        
    def tearDown(self):
        self.conn.close()
        
    def test_dependencies(self):
        # A depends on B (hop 1) and C (hop 1)
        # B depends on D (hop 2 from A)
        # D depends on E (hop 3 from A)
        res = graph_trace(self.conn, "A", depth=3)
        
        deps = {item["file_path"]: item["hop"] for item in res["dependencies"]}
        self.assertEqual(deps.get("B"), 1)
        self.assertEqual(deps.get("C"), 1)
        self.assertEqual(deps.get("D"), 2)
        self.assertEqual(deps.get("E"), 3)
        self.assertNotIn("external_lib", deps)
        
    def test_dependents(self):
        # F imports A. So F is dependent on A (hop 1).
        res = graph_trace(self.conn, "A", depth=3)
        
        dependents = {item["file_path"]: item["hop"] for item in res["dependents"]}
        self.assertEqual(dependents.get("F"), 1)
        
    def test_depth_cap(self):
        # With depth=2, we shouldn't reach E (which is hop 3).
        res = graph_trace(self.conn, "A", depth=2)
        
        deps = {item["file_path"]: item["hop"] for item in res["dependencies"]}
        self.assertIn("B", deps)
        self.assertIn("C", deps)
        self.assertIn("D", deps)
        self.assertNotIn("E", deps) # excluded due to depth limit
        self.assertTrue(res["depth_capped"])
        
    def test_empty_edges(self):
        # Z has no connections
        res = graph_trace(self.conn, "Z", depth=3)
        self.assertEqual(res["dependents"], [])
        self.assertEqual(res["dependencies"], [])
        self.assertFalse(res["depth_capped"])

    def test_resolve_import_path_javascript(self):
        from server.indexer.graph_builder import resolve_import_path
        known_paths = {
            "backend/src/middleware/auth.js",
            "backend/src/utils/jwt.js",
            "frontend/src/context/AuthContext.tsx"
        }
        
        # Test .js importing .js relatively
        res = resolve_import_path("backend/src/middleware/auth.js", "../utils/jwt", known_paths)
        self.assertEqual(res, "backend/src/utils/jwt.js")
        
        # Test .js importing with exact match
        res = resolve_import_path("backend/src/middleware/auth.js", "backend/src/utils/jwt.js", known_paths)
        self.assertEqual(res, "backend/src/utils/jwt.js")
        
        # Test .tsx relative import
        res = resolve_import_path("frontend/src/context/AuthContext.tsx", "./AuthContext", known_paths)
        self.assertEqual(res, "frontend/src/context/AuthContext.tsx")

if __name__ == "__main__":
    unittest.main()
