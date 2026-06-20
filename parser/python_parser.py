import os
from typing import List, Dict, Any
from tree_sitter_languages import get_parser

# Initialize the parser
parser = get_parser("python")

def parse_python_file(file_path: str, repo_path: str = "") -> Dict[str, Any]:
    """
    Parses a Python file using tree-sitter to extract its imports, functions, classes, and exports.
    """
    # Read file content
    full_path = os.path.join(repo_path, file_path) if repo_path else file_path
    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()
        
    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node
    
    imports: List[Dict[str, Any]] = []
    functions: List[str] = []
    classes: List[str] = []
    exports: List[str] = []
    
    # Track imports by module to merge duplicates
    imports_by_module: Dict[str, set] = {}
    
    # Track symbol line ranges (1-indexed)
    symbol_line_spans: Dict[str, Dict[str, int]] = {}

    def extract_dotted_name(node) -> str:
        return node.text.decode("utf8").strip()

    def process_import_statement(node):
        # Format: import os, sys.path as sp
        # We look for dotted_name or aliased_import
        for child in node.children:
            if child.type == "dotted_name":
                module = extract_dotted_name(child)
                if module not in imports_by_module:
                    imports_by_module[module] = set()
            elif child.type == "aliased_import":
                # Find the dotted_name inside the aliased_import
                dotted_node = child.child_by_field_name("name")
                if not dotted_node:
                    # Fallback to search children
                    for c in child.children:
                        if c.type == "dotted_name":
                            dotted_node = c
                            break
                if dotted_node:
                    module = extract_dotted_name(dotted_node)
                    if module not in imports_by_module:
                        imports_by_module[module] = set()

    def process_import_from_statement(node):
        # Format: from x.y import z, w as q
        # module_name is a field, or first dotted_name / relative_import child
        module_node = node.child_by_field_name("module_name")
        if not module_node:
            for child in node.children:
                if child.type in ("dotted_name", "relative_import"):
                    module_node = child
                    break
        
        if not module_node:
            return
            
        module_name = extract_dotted_name(module_node)
        
        if module_name not in imports_by_module:
            imports_by_module[module_name] = set()
            
        # Collect all imported names. They occur after the import keyword
        # Let's find all children of type dotted_name, aliased_import, wildcard_import,
        # or parenthesized_import_list that are positioned after module_node
        found_import_keyword = False
        for child in node.children:
            if child.type == "import":
                found_import_keyword = True
                continue
            if not found_import_keyword:
                continue
                
            # Now we are looking at imported names
            def collect_names(n):
                if n.type == "dotted_name":
                    imports_by_module[module_name].add(extract_dotted_name(n))
                elif n.type == "aliased_import":
                    name_node = n.child_by_field_name("name")
                    if not name_node:
                        for c in n.children:
                            if c.type == "dotted_name":
                                name_node = c
                                break
                    if name_node:
                        imports_by_module[module_name].add(extract_dotted_name(name_node))
                elif n.type == "wildcard_import":
                    imports_by_module[module_name].add("*")
                elif n.type in ("parenthesized_import_list", "import_list"):
                    for c in n.children:
                        collect_names(c)
                        
            collect_names(child)

    def traverse(node):
        # Process imports
        if node.type == "import_statement":
            process_import_statement(node)
        elif node.type == "import_from_statement":
            process_import_from_statement(node)
            
        # Process functions
        elif node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = name_node.text.decode("utf8").strip()
                functions.append(func_name)
                # Public functions (not starting with _) are exports
                if not func_name.startswith("_"):
                    exports.append(func_name)
                
                # Record line range (1-indexed)
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                symbol_line_spans[func_name] = {
                    "start_line": start_line,
                    "end_line": end_line
                }
            # Traverse function children (to look for nested functions/classes, though we usually care about top-level mostly)
            # Let's traverse only children that are not the block body to avoid extracting local functions.
            # Spec says "function_definition (name only), class_definition (name only)".
            # Wait, do we want nested functions? The spec says:
            # "Extract: all function_definition nodes at module level and class level -> name only, skip body".
            # To skip body, we shouldn't traverse into the `body` node!
            # In python, function_definition has a `body` field. Let's skip it.
            for child in node.children:
                if child.type != "block":
                    traverse(child)
            return

        # Process classes
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                class_name = name_node.text.decode("utf8").strip()
                classes.append(class_name)
                # Public classes are exports
                if not class_name.startswith("_"):
                    exports.append(class_name)
                
                # Record line range (1-indexed)
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                symbol_line_spans[class_name] = {
                    "start_line": start_line,
                    "end_line": end_line
                }
            # Traverse class body to extract methods (functions inside class)
            body_node = node.child_by_field_name("body")
            if body_node:
                traverse(body_node)
            # Process class definition children (e.g. decorators, superclasses) but not the main body again
            for child in node.children:
                if child.type != "block":
                    traverse(child)
            return

        # Regular recursive traversal for other nodes
        for child in node.children:
            traverse(child)

    traverse(root_node)
    
    # Convert imports_by_module dictionary to the list format
    for mod, names in imports_by_module.items():
        imports.append({
            "module": mod,
            "names": sorted(list(names))
        })
        
    return {
        "file_path": file_path.replace(os.sep, '/'),
        "language": "python",
        "imports": imports,
        "exports": exports,
        "functions": functions,
        "classes": classes,
        "symbol_line_spans": symbol_line_spans
    }

if __name__ == "__main__":
    # Test script in place
    import sys
    import json
    if len(sys.argv) > 1:
        blueprint = parse_python_file(sys.argv[1])
        print(json.dumps(blueprint, indent=2))
