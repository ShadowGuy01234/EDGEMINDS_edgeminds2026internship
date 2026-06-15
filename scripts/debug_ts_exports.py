from tree_sitter_languages import get_parser
parser = get_parser("tsx")
code = """
export default class MyDefaultClass {}
export class PublicClass {}
export function publicFunc() {}
export const Header = () => {};
"""
tree = parser.parse(bytes(code, "utf8"))

def print_node(node, depth=0):
    print("  " * depth + f"{node.type} ({node.text.decode('utf8').splitlines()[0]})")
    for child in node.children:
        print_node(child, depth + 1)

print_node(tree.root_node)
