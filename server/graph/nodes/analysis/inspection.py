import os
from typing import Dict, Any, List
from server.graph.state import GraphState
from server.database.sqlite_manager import SqliteManager
from server.logger.logger import logging

DB_PATH = "server/data/codebase_intelligence.db"

def build_tree(path: str, base_path: str) -> Dict[str, Any]:
    """Helper recursively building the directory tree structure."""
    name = os.path.basename(path)
    rel_path = os.path.relpath(path, base_path).replace("\\", "/")
    if rel_path == ".":
        rel_path = ""
        
    if os.path.isdir(path):
        children = []
        try:
            for item in sorted(os.listdir(path)):
                # Ignore noisy metadata, libraries, or caches
                if item in ['.git', 'node_modules', 'venv', '__pycache__', '.venv', '.agents', '.gemini', 'dist', 'build']:
                    continue
                child_tree = build_tree(os.path.join(path, item), base_path)
                children.append(child_tree)
        except Exception as e:
            logging.warning(f"Could not list directory {path}: {e}")
        return {"name": name or "root", "type": "directory", "path": rel_path, "children": children}
    else:
        size = 0
        try:
            size = os.path.getsize(path)
        except Exception:
            pass
        return {"name": name, "type": "file", "path": rel_path, "size": size}

def analysis_repository_inspector(state: GraphState) -> Dict[str, Any]:
    """
    Node 3: Scans the filesystem, lists files, and builds the directory tree structure.
    """
    logging.info("Running node: analysis_repository_inspector")
    repo_id = state["repository_id"]
    repo_path = state["repository_path"]
    
    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "inspecting")
    
    if not repo_path or not os.path.exists(repo_path):
        return {"errors": ["Cloned repository directory not found."]}

    # Crawl files and build tree
    directory_tree = build_tree(repo_path, repo_path)
    
    # Flatten the tree to a list of files with their path and size
    files_list = []
    file_metadata_dict = {}
    
    def flatten_tree(node):
        if node["type"] == "file":
            path = node["path"]
            files_list.append(path)
            file_metadata_dict[path] = {
                "size": node.get("size", 0),
                "name": node["name"]
            }
        else:
            for child in node.get("children", []):
                flatten_tree(child)
                
    flatten_tree(directory_tree)
    logging.info(f"Inspector found {len(files_list)} files.")

    return {
        "directory_tree": directory_tree,
        "files": files_list,
        "file_metadata": file_metadata_dict,
        "analysis_status": "inspecting",
        "errors": []
    }

def get_file_classification(file_path: str) -> str:
    """Classifies a file path into a type based on name or extension."""
    filename = os.path.basename(file_path).lower()
    _, ext = os.path.splitext(filename)
    
    # Special config/manifest names
    if filename in ["package.json", "composer.json", "pom.xml", "build.gradle", "go.mod", "cargo.toml", "requirements.txt", "pipfile", "pyproject.toml"]:
        return "manifest"
    if filename in ["dockerfile", "docker-compose.yml", "docker-compose.yaml"]:
        return "docker"
    if filename in [".env", ".env.example", ".env.local"]:
        return "environment"
        
    # Standard extensions
    if ext in [".py", ".pyw"]:
        return "python"
    if ext in [".js", ".mjs"]:
        return "javascript"
    if ext in [".ts"]:
        return "typescript"
    if ext in [".tsx"]:
        return "react-ts"
    if ext in [".jsx"]:
        return "react-js"
    if ext in [".java"]:
        return "java"
    if ext in [".cpp", ".cc", ".cxx", ".c", ".h", ".hpp"]:
        return "cpp"
    if ext in [".html", ".htm", ".css", ".scss", ".sass"]:
        return "web-static"
    if ext in [".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".xml"]:
        return "config"
    if ext in [".md", ".txt", ".rst", ".pdf", ".docx"]:
        return "documentation"
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".zip", ".tar", ".gz", ".exe", ".dll", ".so", ".dylib", ".bin"]:
        return "binary"
        
    return "unknown"

def analysis_file_classifier(state: GraphState) -> Dict[str, Any]:
    """
    Node 4: Classifies each file to decide how it is analyzed.
    """
    logging.info("Running node: analysis_file_classifier")
    repo_id = state["repository_id"]
    files = state.get("files") or []
    file_metadata = state.get("file_metadata") or {}
    
    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "parsing")

    # Update metadata with classification type
    updated_metadata = {}
    for f_path in files:
        meta = file_metadata.get(f_path, {})
        meta["type"] = get_file_classification(f_path)
        updated_metadata[f_path] = meta
        
    return {
        "file_metadata": updated_metadata,
        "analysis_status": "parsing"
    }
