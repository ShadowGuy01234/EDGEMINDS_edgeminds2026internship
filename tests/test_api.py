import os
import json
import unittest
from fastapi.testclient import TestClient

from api.main import app
from api.config import DB_PATH

class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        
    def test_get_status(self):
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("index_loaded", data)
        self.assertIn("repo_path", data)
        self.assertIn("ollama_reachable", data)
        self.assertIn("memory_used_mb", data)
        
    def test_get_files(self):
        response = self.client.get("/files")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("files", data)
        self.assertTrue(isinstance(data["files"], list))
        if len(data["files"]) > 0:
            item = data["files"][0]
            self.assertIn("path", item)
            self.assertIn("language", item)
            self.assertIn("function_count", item)
            self.assertIn("class_count", item)
            
    def test_get_history(self):
        response = self.client.get("/history")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("history", data)
        self.assertTrue(isinstance(data["history"], list))
        
    def test_post_query_success(self):
        # We query for something that should exist since we already built the index
        payload = {"query": "Find the python parser"}
        response = self.client.post("/query", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "Find the python parser")
        self.assertIn("tool_used", data)
        self.assertIn("routed_by", data)
        self.assertIn("seed", data)
        self.assertIn("symbol_matches", data)
        
    def test_post_query_empty(self):
        response = self.client.post("/query", json={"query": ""})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "error")
        
    def test_post_ingest_not_found(self):
        payload = {"repo_path": "/nonexistent/repo/path/here"}
        response = self.client.post("/ingest", json=payload)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error"], "repo_not_found")
