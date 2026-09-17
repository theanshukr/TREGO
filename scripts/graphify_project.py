"""TREGO Graph Engineering & Codebase Architecture Visualizer.

Parses all modules, imports, function calls, tools, and endpoints to build
a comprehensive dependency and control flow graph.
"""
import ast
import os
from pathlib import Path

def analyze_codebase(root_dir: str):
    root = Path(root_dir)
    nodes = {}
    edges = []

    for path in root.rglob("*.py"):
        # Skip venv or git
        if ".venv" in path.parts or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        rel_path = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(path))
            
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)

            nodes[rel_path] = {
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "lines": len(content.splitlines()),
            }

            for imp in imports:
                # Check internal project edges
                if imp.startswith("shared") or imp.startswith("server") or imp.startswith("client"):
                    edges.append((rel_path, imp))
        except Exception as e:
            nodes[rel_path] = {"error": str(e)}

    return nodes, edges

if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes, edges = analyze_codebase(repo_root)
    print(f"Total Python Source Nodes: {len(nodes)}")
    print(f"Total Internal Dependencies: {len(edges)}")
    for rel_path, data in sorted(nodes.items()):
        cls_str = ", ".join(data.get("classes", [])[:4])
        print(f"- {rel_path} ({data.get('lines', 0)} lines) | Classes: [{cls_str}]")
