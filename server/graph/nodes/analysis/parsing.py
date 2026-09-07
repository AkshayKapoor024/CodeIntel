import os
import ast
import re
from typing import Dict, Any, List
from server.graph.state import GraphState
from server.database.sqlite_manager import SqliteManager
from server.logger.logger import logging

DB_PATH = "server/data/codebase_intelligence.db"

def parse_python_file(content: str) -> Dict[str, Any]:
    """Parses Python source code and extracts structural elements using Python ast module."""
    try:
        root = ast.parse(content)
    except Exception as e:
        return {"error": f"Syntax error: {str(e)}"}

    classes = []
    functions = []
    imports = []
    calls = []
    line_mappings = []

    for node in ast.walk(root):
        if isinstance(node, ast.ClassDef):
            methods = []
            for n in node.body:
                if isinstance(n, ast.FunctionDef):
                    methods.append(n.name)
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except Exception:
                    pass
            classes.append({
                "name": node.name,
                "methods": methods,
                "bases": bases,
                "line": getattr(node, "lineno", 1)
            })
            line_mappings.append({"type": "class", "name": node.name, "line": getattr(node, "lineno", 1)})
            
        elif isinstance(node, ast.FunctionDef):
            # Exclude methods (we check if they are in classes elsewhere or just list them here too)
            args = [arg.arg for arg in node.args.args]
            decorators = []
            for d in node.decorator_list:
                try:
                    decorators.append(ast.unparse(d))
                except Exception:
                    pass
            functions.append({
                "name": node.name,
                "args": args,
                "decorators": decorators,
                "line": getattr(node, "lineno", 1)
            })
            line_mappings.append({"type": "function", "name": node.name, "line": getattr(node, "lineno", 1)})

        elif isinstance(node, ast.Import):
            for name in node.names:
                imports.append(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)

    return {
        "classes": classes,
        "functions": functions,
        "imports": list(set(imports)),
        "calls": list(set(calls)),
        "line_mappings": line_mappings
    }

def parse_jsts_file(content: str) -> Dict[str, Any]:
    """Parses JavaScript/TypeScript/React source code and extracts structural elements using regex."""
    # Find import statements e.g. import foo from './bar' or require('bar')
    imports = re.findall(r'(?:import|from)\s+[\'"]([^\'"]+)[\'"]', content)
    requires = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content)
    all_imports = list(set(imports + requires))

    # Find functions
    # function name(...)
    func_pattern1 = re.findall(r'\bfunction\s+(\w+)\s*\(', content)
    # const name = (...) =>
    func_pattern2 = re.findall(r'\b(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|\w+)\s*=>', content)
    funcs = list(set(func_pattern1 + func_pattern2))

    # Find classes
    classes_pattern = re.findall(r'\bclass\s+(\w+)', content)
    
    # React Hooks e.g. useState, useEffect, useMyHook
    hooks = re.findall(r'\b(use[A-Z]\w+)\b', content)
    
    # React Components (functions returning JSX, capital letter name)
    components = re.findall(r'\bconst\s+([A-Z]\w+)\s*=\s*\([^)]*\)\s*=>\s*\(?', content)

    # Exports
    exports = re.findall(r'\bexport\s+(?:default\s+)?(?:const|class|function)?\s*(\w+)', content)

    classes_list = [{"name": c} for c in classes_pattern]
    functions_list = [{"name": f} for f in funcs]

    # Dummy line mapping based on index search
    line_mappings = []
    lines = content.splitlines()
    for item in classes_pattern:
        for idx, line in enumerate(lines):
            if f"class {item}" in line:
                line_mappings.append({"type": "class", "name": item, "line": idx + 1})
                break
    for item in funcs:
        for idx, line in enumerate(lines):
            if f"function {item}" in line or f"{item} =" in line:
                line_mappings.append({"type": "function", "name": item, "line": idx + 1})
                break

    return {
        "classes": classes_list,
        "functions": functions_list,
        "imports": all_imports,
        "exports": list(set(exports)),
        "react_hooks": list(set(hooks)),
        "react_components": list(set(components)),
        "line_mappings": line_mappings
    }

def analysis_source_parser(state: GraphState) -> Dict[str, Any]:
    """
    Node 5: Parses files based on their classification and builds structural maps.
    """
    logging.info("Running node: analysis_source_parser")
    repo_id = state["repository_id"]
    repo_path = state["repository_path"]
    files = state.get("files") or []
    file_metadata = state.get("file_metadata") or {}

    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "parsing")

    ast_data = {}
    
    for f_path in files:
        meta = file_metadata.get(f_path, {})
        f_type = meta.get("type", "unknown")
        
        full_path = os.path.join(repo_path, f_path)
        if not os.path.exists(full_path):
            continue
            
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            if f_type == "python":
                ast_data[f_path] = parse_python_file(content)
            elif f_type in ["javascript", "typescript", "react-js", "react-ts"]:
                ast_data[f_path] = parse_jsts_file(content)
            else:
                # Basic parsing: extract imports/dependencies using generic regex
                imports = re.findall(r'(?:import|from|require)\s+[\'"]([^\'"]+)[\'"]', content)
                ast_data[f_path] = {
                    "classes": [],
                    "functions": [],
                    "imports": list(set(imports)),
                    "line_mappings": []
                }
        except Exception as e:
            logging.error(f"Error parsing file {f_path}: {e}")
            ast_data[f_path] = {"error": str(e)}

    return {
        "ast_data": ast_data,
        "analysis_status": "analyzing"
    }
