import os
import json
from typing import Dict, Any, List
from server.graph.state import GraphState
from server.database.sqlite_manager import SqliteManager
from server.logger.logger import logging
from server.core.llms import openai_accuracy_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

DB_PATH = "server/data/codebase_intelligence.db"

def analysis_architecture_analyzer(state: GraphState) -> Dict[str, Any]:
    """
    Node 8: Analyzes the codebase architecture at a high level of abstraction, 
    inferring layer separation, DB layer, routing, and tech stack.
    """
    logging.info("Running node: analysis_architecture_analyzer")
    repo_id = state["repository_id"]
    repo_path = state["repository_path"]
    files = state.get("files") or []
    file_metadata = state.get("file_metadata") or {}

    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "analyzing_architecture")

    # 1. Compute Technology Stack based on file classifications
    tech_stack = {}
    for f_path in files:
        meta = file_metadata.get(f_path, {})
        f_type = meta.get("type", "unknown")
        if f_type != "unknown":
            tech_stack[f_type] = tech_stack.get(f_type, 0) + 1

    # 2. Extract contents of manifests to identify frameworks
    manifest_contents = ""
    manifest_files = ["package.json", "requirements.txt", "pyproject.toml", "go.mod", "Cargo.toml"]
    
    for f_path in files:
        filename = os.path.basename(f_path)
        if filename in manifest_files:
            full_path = os.path.join(repo_path, f_path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                manifest_contents += f"\n--- {f_path} ---\n{content[:1500]}\n"
            except Exception as e:
                logging.warning(f"Could not read manifest {f_path}: {e}")

    # 3. Create high-level directory outline for context
    dir_structure = ""
    # Look at root-level files and directories
    try:
        root_items = sorted(os.listdir(repo_path))
        dir_structure = "Root directory contents: " + ", ".join(root_items)
    except Exception:
        pass

    # 4. Query LLM to reason on Architecture Layout
    arch_prompt = """
    You are an expert software architect. Analyze the file layout, tech stack, and manifest configurations of this repository.
    
    **Directory Outline**:
    {dir_structure}
    
    **File Type Distribution**:
    {tech_stack}
    
    **Package Manifest Contents**:
    {manifest_contents}
    
    Provide your analysis strictly in JSON format matching this schema:
    {{
      "style": "Monolithic, Microservices, Serverless, Full-stack Single Repo, etc.",
      "frontend_backend": "Details on frontend/backend separation (e.g. React client and FastAPI server, mixed MVC, etc.)",
      "database": "Details of the database layers used, if any (e.g. SQLite, PostgreSQL, MongoDB, ORM choices)",
      "auth_flow": "Details on authentication flows (e.g. JWT session cookies, OAuth, no auth found)",
      "overview": "A clear, descriptive architectural summary of how components interact."
    }}
    """
    
    prompt = ChatPromptTemplate.from_template(arch_prompt)
    chain = prompt | openai_accuracy_chain | JsonOutputParser()
    
    try:
        arch_analysis = chain.invoke({
            "dir_structure": dir_structure,
            "tech_stack": json.dumps(tech_stack),
            "manifest_contents": manifest_contents
        })
        # Inject tech stack file counts
        arch_analysis["technology_stack"] = tech_stack
    except Exception as e:
        logging.error(f"Failed architecture analysis: {e}")
        # Return fallback architecture summary
        arch_analysis = {
            "style": "General Codebase",
            "frontend_backend": "Contains source files in the repository",
            "database": "Not explicitly detected",
            "auth_flow": "Not explicitly detected",
            "overview": "A software codebase folder structure containing multiple directories and files.",
            "technology_stack": tech_stack
        }

    return {
        "architecture_analysis": arch_analysis,
        "analysis_status": "quality_check"
    }
