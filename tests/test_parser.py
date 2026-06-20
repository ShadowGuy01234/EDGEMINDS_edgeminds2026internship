import os
import tempfile
import json
import unittest

from server.parser.python_parser import parse_python_file
from server.parser.typescript_parser import parse_typescript_file
from server.parser.file_scanner import scan_repo
from server.parser.ingest import ingest_repository

class TestASTParsers(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for test files
        self.test_dir = tempfile.TemporaryDirectory()
        self.repo_path = self.test_dir.name
        
    def tearDown(self):
        self.test_dir.cleanup()
        
    def test_python_parser(self):
        # Create a mock Python file
        py_content = """
import os
import sys as system
from datetime import datetime, timezone
from jwt import decode, encode

class _PrivateClass:
    pass

class PublicClass:
    def __init__(self):
        pass
    def class_method(self, x):
        return x

def _private_func():
    pass

def public_func(y):
    # A comment
    return y
"""
        py_file_path = os.path.join(self.repo_path, "test_file.py")
        with open(py_file_path, "w", encoding="utf-8") as f:
            f.write(py_content)
            
        blueprint = parse_python_file("test_file.py", self.repo_path)
        
        self.assertEqual(blueprint["file_path"], "test_file.py")
        self.assertEqual(blueprint["language"], "python")
        
        # Check imports
        imports = {imp["module"]: set(imp["names"]) for imp in blueprint["imports"]}
        self.assertIn("os", imports)
        self.assertIn("sys", imports)
        self.assertIn("datetime", imports)
        self.assertIn("jwt", imports)
        self.assertEqual(imports["jwt"], {"decode", "encode"})
        
        # Check functions
        self.assertIn("public_func", blueprint["functions"])
        self.assertIn("_private_func", blueprint["functions"])
        self.assertIn("class_method", blueprint["functions"])
        
        # Check classes
        self.assertIn("PublicClass", blueprint["classes"])
        self.assertIn("_PrivateClass", blueprint["classes"])
        
        # Check exports
        self.assertIn("PublicClass", blueprint["exports"])
        self.assertIn("public_func", blueprint["exports"])
        self.assertNotIn("_private_func", blueprint["exports"])
        self.assertNotIn("_PrivateClass", blueprint["exports"])

    def test_typescript_parser(self):
        # Create a mock TypeScript/TSX file
        ts_content = """
import defaultVal, { name1, name2 as alias } from "module-a";
import * as ns from "module-b";
import "module-c";

export default class MyDefaultClass {
    constructor() {}
    classMethod() {}
}

export class PublicClass {}

export function publicFunc() {}

const localArrow = () => {};

export const Header = () => {
    return <div>Hello</div>;
};
"""
        ts_file_path = os.path.join(self.repo_path, "test_file.tsx")
        with open(ts_file_path, "w", encoding="utf-8") as f:
            f.write(ts_content)
            
        blueprint = parse_typescript_file("test_file.tsx", self.repo_path)
        
        self.assertEqual(blueprint["file_path"], "test_file.tsx")
        self.assertEqual(blueprint["language"], "typescript")
        
        # Check imports
        imports = {imp["module"]: set(imp["names"]) for imp in blueprint["imports"]}
        self.assertIn("module-a", imports)
        self.assertIn("module-b", imports)
        self.assertIn("module-c", imports)
        self.assertIn("defaultVal", imports["module-a"])
        self.assertIn("name1", imports["module-a"])
        self.assertIn("name2", imports["module-a"])
        self.assertIn("*", imports["module-b"])
        
        # Check functions
        self.assertIn("publicFunc", blueprint["functions"])
        self.assertIn("classMethod", blueprint["functions"])
        self.assertIn("Header", blueprint["functions"])
        
        # Check classes
        self.assertIn("MyDefaultClass", blueprint["classes"])
        self.assertIn("PublicClass", blueprint["classes"])
        
        # Check exports
        self.assertIn("default", blueprint["exports"])
        self.assertIn("PublicClass", blueprint["exports"])
        self.assertIn("publicFunc", blueprint["exports"])
        self.assertIn("Header", blueprint["exports"])

    def test_file_scanner(self):
        # Create some nested files
        os.makedirs(os.path.join(self.repo_path, "src", "auth"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_path, ".git"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_path, "node_modules"), exist_ok=True)
        
        # Create files
        open(os.path.join(self.repo_path, "src", "auth", "middleware.py"), "w").close()
        open(os.path.join(self.repo_path, "src", "app.ts"), "w").close()
        open(os.path.join(self.repo_path, "README.md"), "w").close() # should be ignored by extension
        open(os.path.join(self.repo_path, ".git", "config"), "w").close() # should be ignored by dir
        open(os.path.join(self.repo_path, "node_modules", "package.json"), "w").close() # ignored by dir
        
        # Large file
        with open(os.path.join(self.repo_path, "large.py"), "w") as f:
            f.write("A" * 600 * 1024) # 600KB
            
        files = scan_repo(self.repo_path)
        
        self.assertIn("src/auth/middleware.py", files)
        self.assertIn("src/app.ts", files)
        self.assertNotIn("README.md", files)
        self.assertNotIn(".git/config", files)
        self.assertNotIn("node_modules/package.json", files)
        self.assertNotIn("large.py", files)

if __name__ == "__main__":
    unittest.main()
