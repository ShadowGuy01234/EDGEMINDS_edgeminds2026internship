import unittest
import sqlite3
from unittest.mock import MagicMock, patch

from engine.executor import execute
from router.fallback import RouterDecision

class TestQueryExecutor(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.embedder = MagicMock()
        
    def tearDown(self):
        self.conn.close()

    @patch("engine.executor.vector_search")
    @patch("engine.executor.graph_trace")
    def test_vector_only_path(self, mock_graph, mock_vector):
        # Decision: pure vector search
        decision = RouterDecision(
            tool="vector",
            keywords=["JWT", "decode"],
            routed_by="slm",
            slm_raw="Where is JWT decode?",
            latency_ms=100
        )
        
        # Setup mock vector results
        mock_vector.return_value = [
            {"name": "decode_token", "file_path": "src/auth.py", "kind": "function", "similarity": 0.9}
        ]
        
        res = execute(self.conn, self.embedder, decision)
        
        # Assertions
        self.assertEqual(res["tool_used"], "vector")
        self.assertEqual(res["routed_by"], "slm")
        self.assertFalse(res["no_match"])
        self.assertEqual(res["seed"]["symbol"], "decode_token")
        self.assertEqual(res["seed"]["file_path"], "src/auth.py")
        self.assertEqual(len(res["symbol_matches"]), 1)
        self.assertEqual(res["dependents"], [])
        self.assertEqual(res["dependencies"], [])
        
        # Verify graph search was NOT executed
        mock_graph.assert_not_called()
        mock_vector.assert_called_once()

    @patch("engine.executor.vector_search")
    @patch("engine.executor.graph_trace")
    def test_graph_only_path(self, mock_graph, mock_vector):
        # Decision: graph traversal
        decision = RouterDecision(
            tool="graph",
            keywords=["config", "imports"],
            routed_by="fallback",
            slm_raw="What imports config?",
            latency_ms=200
        )
        
        # Setup mocks
        mock_vector.return_value = [
            {"name": "config", "file_path": "src/config.py", "kind": "export", "similarity": 0.8}
        ]
        mock_graph.return_value = {
            "dependents": [{"file_path": "src/app.py", "hop": 1}],
            "dependencies": [],
            "depth_capped": False
        }
        
        res = execute(self.conn, self.embedder, decision)
        
        self.assertEqual(res["tool_used"], "graph")
        self.assertEqual(res["routed_by"], "fallback")
        self.assertEqual(res["seed"]["file_path"], "src/config.py")
        self.assertEqual(res["symbol_matches"], []) # Graph tool returns empty symbol list
        self.assertEqual(len(res["dependents"]), 1)
        self.assertEqual(res["dependents"][0]["file_path"], "src/app.py")
        
        mock_vector.assert_called_once_with(self.conn, self.embedder, ["config", "imports"], top_k=1, has_vss=False)
        mock_graph.assert_called_once_with(self.conn, "src/config.py", depth=3)

    @patch("engine.executor.vector_search")
    @patch("engine.executor.graph_trace")
    def test_hybrid_path(self, mock_graph, mock_vector):
        # Decision: hybrid path
        decision = RouterDecision(
            tool="hybrid",
            keywords=["middleware"],
            routed_by="slm",
            slm_raw="Find middleware relations",
            latency_ms=50
        )
        
        # Setup mocks
        mock_vector.return_value = [
            {"name": "AuthMiddleware", "file_path": "src/middleware.py", "kind": "class", "similarity": 0.85},
            {"name": "LoggerMiddleware", "file_path": "src/middleware.py", "kind": "class", "similarity": 0.70}
        ]
        mock_graph.return_value = {
            "dependents": [],
            "dependencies": [{"file_path": "src/db.py", "hop": 1}],
            "depth_capped": False
        }
        
        res = execute(self.conn, self.embedder, decision)
        
        self.assertEqual(res["tool_used"], "hybrid")
        self.assertEqual(res["seed"]["symbol"], "AuthMiddleware") # Seed is top match
        self.assertEqual(len(res["symbol_matches"]), 2)
        self.assertEqual(len(res["dependencies"]), 1)
        
        mock_vector.assert_called_once_with(self.conn, self.embedder, ["middleware"], top_k=10, has_vss=False)
        mock_graph.assert_called_once_with(self.conn, "src/middleware.py", depth=3)

    @patch("engine.executor.vector_search")
    def test_no_match_scenario(self, mock_vector):
        # Decision: vector search with no matches
        decision = RouterDecision(
            tool="hybrid",
            keywords=["nonexistent"],
            routed_by="slm",
            slm_raw="Query for nonexistent symbol",
            latency_ms=80
        )
        
        # Setup mock vector to return empty list
        mock_vector.return_value = []
        
        res = execute(self.conn, self.embedder, decision)
        
        self.assertTrue(res["no_match"])
        self.assertIsNone(res["seed"])
        self.assertEqual(res["symbol_matches"], [])
        self.assertEqual(res["dependents"], [])
        self.assertEqual(res["dependencies"], [])

if __name__ == "__main__":
    unittest.main()
