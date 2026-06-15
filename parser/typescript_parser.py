import os
from typing import List, Dict, Any
from tree_sitter_languages import get_parser

# Initialize TS and TSX parsers
ts_parser = get_parser("typescript")
tsx_parser = get_parser("tsx")

def parse_typescript_file(file_path: str, repo_path: str = "") -> Dict[str, Any]:
    """
    Parses a TypeScript/TSX file using tree-sitter to extract imports, functions, classes, and exports.
    """
    full_path = os.path.join(repo_path, file_path) if repo_path else file_path
    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()
        
    ext = os.path.splitext(file_path)[1].lower()
    # Use tsx parser for .tsx and .jsx files, ts parser for .ts and .js files
    parser = tsx_parser if ext in (".tsx", ".jsx") else ts_parser
    
    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node
    
    imports: List[Dict[str, Any]] = []
    functions: List[str] = []
    classes: List[str] = []
    exports: List[str] = []
    
    imports_by_module: Dict[str, set] = {}

    def extract_string_literal(node) -> str:
        text = node.text.decode("utf8").strip()
        if len(text) >= 2 and ((text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'")):
            return text[1:-1]
        return text

    def process_import_statement(node):
        # Format: import defaultVal, { name1, name2 as alias } from "module";
        source_node = None
        for child in node.children:
            if child.type == "string":
                source_node = child
                break
        if not source_node:
            return
            
        module_name = extract_string_literal(source_node)
        if module_name not in imports_by_module:
            imports_by_module[module_name] = set()
            
        # Extract names from import_clause
        clause_node = node.child_by_field_name("import_clause")
        if not clause_node:
            # Check if there is an import_clause among children
            for child in node.children:
                if child.type == "import_clause":
                    clause_node = child
                    break
        if not clause_node:
            return
            
        # 1. Default import: child identifier directly under import_clause
        for child in clause_node.children:
            if child.type == "identifier":
                imports_by_module[module_name].add(child.text.decode("utf8").strip())
                
        # 2. Namespace import: * as ns
        for child in clause_node.children:
            if child.type == "namespace_import":
                imports_by_module[module_name].add("*")
                break
            
        # 3. Named imports: { name1, name2 as alias }
        named_node = None
        for child in clause_node.children:
            if child.type == "named_imports":
                named_node = child
                break
        if named_node:
            for spec in named_node.children:
                if spec.type == "import_specifier":
                    # The imported name is the first identifier child of import_specifier
                    name_node = None
                    for c in spec.children:
                        if c.type == "identifier":
                            name_node = c
                            break
                    if name_node:
                        imports_by_module[module_name].add(name_node.text.decode("utf8").strip())

    def extract_variable_declarator_function(decl_node) -> tuple:
        # Checks if variable_declarator is a function or JSX component assignment,
        # e.g., const Header = () => { ... }
        name_node = None
        value_node = None
        for child in decl_node.children:
            if child.type == "identifier":
                name_node = child
            elif child.type in ("arrow_function", "function_expression"):
                value_node = child
                
        if name_node and value_node:
            return name_node.text.decode("utf8").strip(), True
        return None, False

    def process_lexical_declaration(node, is_exported=False):
        # Format: const x = 1, y = () => {}
        for child in node.children:
            if child.type == "variable_declarator":
                var_name, is_func = extract_variable_declarator_function(child)
                if var_name:
                    if is_func:
                        functions.append(var_name)
                    if is_exported:
                        exports.append(var_name)

    def process_export_statement(node):
        # Format:
        # - export default class X {}
        # - export default function f() {}
        # - export default myVar;
        # - export { a, b as c };
        # - export const x = 1;
        # - export function f() {}
        
        is_default = "default" in [c.type for c in node.children]
        
        for child in node.children:
            if child.type == "class_declaration":
                # Find class name
                name_node = None
                for c in child.children:
                    if c.type in ("type_identifier", "identifier"):
                        name_node = c
                        break
                if name_node:
                    name = name_node.text.decode("utf8").strip()
                    classes.append(name)
                    exports.append("default" if is_default else name)
            elif child.type == "function_declaration":
                # Find function name
                name_node = None
                for c in child.children:
                    if c.type == "identifier":
                        name_node = c
                        break
                if name_node:
                    name = name_node.text.decode("utf8").strip()
                    functions.append(name)
                    exports.append("default" if is_default else name)
            elif child.type == "lexical_declaration":
                process_lexical_declaration(child, is_exported=True)
            elif child.type == "export_specifier":
                # E.g. export { a, b as c } -> the name is the first identifier child
                name_node = None
                for c in child.children:
                    if c.type == "identifier":
                        name_node = c
                        break
                if name_node:
                    name = name_node.text.decode("utf8").strip()
                    exports.append("default" if is_default else name)
            elif child.type == "identifier" and is_default:
                # E.g., export default myVar;
                exports.append("default")

    def traverse(node):
        # Process imports
        if node.type in ("import_statement", "import_declaration"):
            process_import_statement(node)
            
        # Process exports
        elif node.type in ("export_statement", "export_declaration", "export_group"):
            process_export_statement(node)
            
        # Process functions
        elif node.type == "function_declaration":
            name_node = None
            for c in node.children:
                if c.type == "identifier":
                    name_node = c
                    break
            if name_node:
                func_name = name_node.text.decode("utf8").strip()
                functions.append(func_name)
            # Skip function body
            for child in node.children:
                if child.type != "statement_block":
                    traverse(child)
            return
            
        # Process classes
        elif node.type == "class_declaration":
            name_node = None
            for c in node.children:
                if c.type in ("type_identifier", "identifier"):
                    name_node = c
                    break
            if name_node:
                class_name = name_node.text.decode("utf8").strip()
                classes.append(class_name)
            # Traverse class body for class methods
            body_node = None
            for child in node.children:
                if child.type == "class_body":
                    body_node = child
                    break
            if body_node:
                traverse(body_node)
            for child in node.children:
                if child.type != "class_body":
                    traverse(child)
            return

        # Process function definitions inside classes (method_definition)
        elif node.type == "method_definition":
            name_node = None
            for c in node.children:
                if c.type in ("property_identifier", "identifier"):
                    name_node = c
                    break
            if name_node:
                method_name = name_node.text.decode("utf8").strip()
                functions.append(method_name)
            # Skip method body
            for child in node.children:
                if child.type != "statement_block":
                    traverse(child)
            return

        # Traverse variables to find module-level arrow functions
        elif node.type == "lexical_declaration":
            # Only process if at root level or within an exported parent (handled in export_statement)
            if node.parent and node.parent.type == "program":
                process_lexical_declaration(node, is_exported=False)

        # Standard traversal
        for child in node.children:
            traverse(child)

    traverse(root_node)
    
    # Convert imports dict to list format
    for mod, names in imports_by_module.items():
        imports.append({
            "module": mod,
            "names": sorted(list(names))
        })
        
    return {
        "file_path": file_path.replace(os.sep, '/'),
        "language": "javascript" if ext in (".js", ".jsx") else "typescript",
        "imports": imports,
        "exports": exports,
        "functions": functions,
        "classes": classes
    }

if __name__ == "__main__":
    # Test script in place
    import sys
    import json
    if len(sys.argv) > 1:
        blueprint = parse_typescript_file(sys.argv[1])
        print(json.dumps(blueprint, indent=2))
