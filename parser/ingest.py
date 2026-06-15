import os
import argparse
import json
import time
from typing import List, Dict, Any

from parser.file_scanner import scan_repo
from parser.python_parser import parse_python_file
from parser.typescript_parser import parse_typescript_file
from parser.layer_classifier import classify_layer

def ingest_repository(repo_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Ingests a repository path, parses all supported files, generates a blueprint manifest,
    and writes error logs if any occur.
    """
    start_time = time.time()
    
    # Standardize absolute paths
    repo_path = os.path.abspath(repo_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    manifest_path = os.path.join(output_dir, "manifest.json")
    error_log_path = os.path.join(output_dir, "parse_errors.log")
    
    # Scan for files
    print(f"Scanning repository: {repo_path}")
    try:
        files = scan_repo(repo_path)
    except Exception as e:
        print(f"Failed to scan repository: {e}")
        return {
            "status": "error",
            "error": "scan_failed",
            "message": str(e),
            "duration_ms": int((time.time() - start_time) * 1000)
        }
        
    print(f"Found {len(files)} files to parse.")
    
    blueprints: List[Dict[str, Any]] = []
    failed_files: List[Dict[str, str]] = []
    
    total_functions = 0
    total_classes = 0
    
    # Process each file
    for rel_path in files:
        ext = os.path.splitext(rel_path)[1].lower()
        try:
            if ext == ".py":
                blueprint = parse_python_file(rel_path, repo_path)
            elif ext in (".ts", ".tsx", ".js", ".jsx"):
                blueprint = parse_typescript_file(rel_path, repo_path)
            else:
                continue
                
            blueprint["layer"] = classify_layer(rel_path)
            blueprints.append(blueprint)
            total_functions += len(blueprint.get("functions", []))
            total_classes += len(blueprint.get("classes", []))
            
        except Exception as e:
            error_msg = f"Failed to parse {rel_path}: {e}"
            print(error_msg)
            failed_files.append({"file_path": rel_path, "error": str(e)})
            
    # Write error log if there were parse failures
    if failed_files:
        with open(error_log_path, "w", encoding="utf-8") as f:
            for item in failed_files:
                f.write(f"File: {item['file_path']}\nError: {item['error']}\n{'-'*40}\n")
        print(f"Logged {len(failed_files)} parsing errors to {error_log_path}")
    else:
        # Clear previous error log if exists
        if os.path.exists(error_log_path):
            os.remove(error_log_path)
            
    # Write manifest.json
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(blueprints, f, indent=2)
        
    duration_ms = int((time.time() - start_time) * 1000)
    
    print(f"\nIngest completed in {duration_ms} ms.")
    print(f"Successfully parsed: {len(blueprints)} files")
    print(f"Failed to parse:     {len(failed_files)} files")
    print(f"Total functions:     {total_functions}")
    print(f"Total classes:       {total_classes}")
    print(f"Manifest written to: {manifest_path}")
    
    return {
        "status": "success",
        "files_parsed": len(blueprints),
        "files_failed": len(failed_files),
        "symbols_indexed": total_functions + total_classes,
        "duration_ms": duration_ms
    }

def main():
    parser = argparse.ArgumentParser(description="Ingest a codebase repository into architectural blueprints.")
    parser.add_argument("--repo", required=True, help="Path to the repository root directory")
    parser.add_argument("--output", default="./index/", help="Path to directory where metadata should be stored")
    
    args = parser.parse_args()
    ingest_repository(args.repo, args.output)

if __name__ == "__main__":
    main()
