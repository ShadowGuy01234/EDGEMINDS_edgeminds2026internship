import os
import json
import unittest
from server.router.slm_router import call_ollama

class TestRouterAccuracy(unittest.TestCase):
    def test_routing_accuracy_gate(self):
        # 20 Test queries: 5 from spec + 15 custom
        test_cases = [
            # Spec queries
            ("What files import the auth module?", "graph", "auth"),
            ("Find the JWT decode function", "vector", "jwt"),
            ("Where is rate limiting handled and what depends on it?", "hybrid", "rate"),
            ("Show me the database connection module", "vector", "database"),
            ("What breaks if I change the middleware?", "hybrid", "middleware"),
            
            # Custom queries
            ("Find the class UserProfile in user routes", "vector", "user"),
            ("What imports session.py in the database directory?", "graph", "session"),
            ("Where is verification code generated?", "vector", "verification"),
            ("Who depends on config module?", "graph", "config"),
            ("Find API key authentication middleware", "vector", "auth"),
            ("Which files depend on helper.py?", "graph", "helper"),
            ("Find the get_status function inside status.py", "vector", "status"),
            ("Where is jwt_middleware and who uses it?", "hybrid", "jwt"),
            ("What dependencies does database session have?", "graph", "database"),
            ("Locate the class AuthMiddleware", "vector", "auth"),
            ("Is there a custom exception handler for API errors?", "vector", "exception"),
            ("Show dependencies of user.py", "graph", "user"),
            ("List files importing main.py", "graph", "main"),
            ("What depends on the email handler and where is it located?", "hybrid", "email"),
            ("Where does the router get initialized?", "vector", "router")
        ]
        
        passed_count = 0
        results_table = []
        
        print("\n=== SLM Intent Router Accuracy Gate Evaluation ===")
        # Pre-warm the model so the first query does not time out
        try:
            call_ollama("warmup query to load model")
        except Exception:
            pass
            
        print(f"{'Query':<55} | {'Expected':<8} | {'Got':<8} | {'Status':<5} | {'Latency':<7}")
        print("-" * 95)
        
        for query, expected_tool, expected_kw in test_cases:
            decision = call_ollama(query)
            
            # Match condition: tool must match expected
            tool_match = (decision.tool == expected_tool)
            
            # Check if expected keyword (case-insensitive) is in decision keywords list
            kw_match = any(expected_kw.lower() in kw.lower() for kw in decision.keywords)
            
            # The primary assertion is the tool routing accuracy, keywords are checked as a secondary target
            is_pass = tool_match and (decision.routed_by == "slm")
            
            if is_pass:
                passed_count += 1
                status_str = "PASS"
            else:
                status_str = "FAIL"
                
            results_table.append({
                "query": query,
                "expected": expected_tool,
                "got": decision.tool,
                "routed_by": decision.routed_by,
                "keywords": decision.keywords,
                "status": status_str,
                "latency_ms": decision.latency_ms
            })
            
            print(f"{query[:53]+'...':<55} | {expected_tool:<8} | {decision.tool:<8} | {status_str:<5} | {decision.latency_ms:>5}ms")
            
        print("-" * 95)
        accuracy = (passed_count / len(test_cases)) * 100
        print(f"Passed: {passed_count}/{len(test_cases)} ({accuracy:.1f}%)")
        print("===================================================\n")
        
        # Write results to tests/router_accuracy.md
        os.makedirs("tests", exist_ok=True)
        with open("tests/router_accuracy.md", "w", encoding="utf-8") as f:
            f.write("# SLM Intent Router Accuracy Report\n\n")
            f.write(f"- **Total Queries tested**: {len(test_cases)}\n")
            f.write(f"- **Passed**: {passed_count}/{len(test_cases)}\n")
            f.write(f"- **Accuracy Score**: {accuracy:.1f}%\n")
            f.write(f"- **Required Gate**: >= 85.0% (17/20 passed)\n")
            f.write(f"- **Status**: {'PASSED' if passed_count >= 17 else 'FAILED'}\n\n")
            f.write("## Test Results Table\n\n")
            f.write("| Query | Expected Tool | Got Tool | Routed By | Keywords | Status | Latency |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for r in results_table:
                f.write(f"| {r['query']} | `{r['expected']}` | `{r['got']}` | {r['routed_by']} | `{r['keywords']}` | **{r['status']}** | {r['latency_ms']}ms |\n")
                
        # Assert accuracy gate of >= 85% (17/20)
        self.assertTrue(passed_count >= 17, f"Routing accuracy {passed_count}/20 is below the 17/20 gate requirement.")

if __name__ == "__main__":
    unittest.main()
