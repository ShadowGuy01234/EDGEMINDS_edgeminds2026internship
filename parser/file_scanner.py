import os
from typing import List

def scan_repo(repo_path: str) -> List[str]:
    """
    Scans a directory path recursively for Python (.py) and TypeScript (.ts, .tsx) files.
    Skips ignored directories and files over 500KB.
    """
    ignored_dirs = {
        'node_modules', '.git', '__pycache__', 'dist', 'build', '.venv', 'venv'
    }
    allowed_extensions = {'.py', '.ts', '.tsx'}
    max_file_size = 500 * 1024  # 500KB
    
    file_list = []
    
    # Resolve real path of repo
    repo_path = os.path.abspath(repo_path)
    if not os.path.exists(repo_path):
        raise FileNotFoundError(f"Repo path '{repo_path}' does not exist.")
        
    for root, dirs, files in os.walk(repo_path):
        # Modify dirs in place to prevent os.walk from visiting ignored directories
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith('.')]
        
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in allowed_extensions:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    if size <= max_file_size:
                        # Return relative or absolute path? Let's normalize relative path from repo_path
                        rel_path = os.path.relpath(file_path, repo_path)
                        # Normalize to forward slashes for cross-platform consistency
                        rel_path = rel_path.replace(os.sep, '/')
                        file_list.append(rel_path)
                except OSError:
                    # Ignore files we cannot access
                    continue
                    
    return file_list

if __name__ == "__main__":
    # Quick manual testing
    import sys
    test_path = sys.argv[1] if len(sys.argv) > 1 else "."
    try:
        files = scan_repo(test_path)
        print(f"Found {len(files)} files:")
        for f in files[:20]:
            print(f" - {f}")
        if len(files) > 20:
            print(" ...")
    except Exception as e:
        print("Error:", e)
