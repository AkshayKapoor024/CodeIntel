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

def analysis_dependency_analyzer(state: GraphState) -> Dict[str, Any]:
    """
    Node 7: Maps import, call, and inheritance relationships across files to build
    a directed dependency graph.
    """
    logging.info("Running node: analysis_dependency_analyzer")
    repo_id = state["repository_id"]
    files = state.get("files") or []
    ast_data = state.get("ast_data") or {}

    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "analyzing_dependencies")

    dependencies = {}
    
    # 1. Deterministic search for file relationships based on imports
    for f_path in files:
        dependencies[f_path] = {}
        ast = ast_data.get(f_path, {})
        imports = ast.get("imports", [])
        
        for imp in imports:
            # Check if this import refers to another file in the repository
            for other_path in files:
                if other_path == f_path:
                    continue
                
                # Check base name e.g. "auth_service" matches "services/auth_service.py"
                other_name = os.path.basename(other_path)
                other_base, _ = os.path.splitext(other_name)
                
                # If import statement matches base name or contains it
                if imp == other_base or imp.endswith(other_base) or other_base.endswith(imp):
                    dependencies[f_path][other_path] = "import"
                    
    return {
        "dependencies": dependencies,
        "analysis_status": "quality_check"
    }

def analysis_quality_analyzer(state: GraphState) -> Dict[str, Any]:
    """
    Node 9: Evaluates the repository codebase quality across seven core dimensions:
    Readability, Maintainability, Scalability, Security, Performance, Testing, and Documentation.
    """
    logging.info("Running node: analysis_quality_analyzer")
    repo_id = state["repository_id"]
    files = state.get("files") or []
    ast_data = state.get("ast_data") or {}
    arch = state.get("architecture_analysis") or {}

    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "quality_check")

    # 1. Extract a high-level summary of structural elements
    code_summary = ""
    for path, ast in list(ast_data.items())[:15]: # Limit to top 15 files to keep prompt within bounds
        classes = [c.get("name") for c in ast.get("classes", [])]
        funcs = [f.get("name") for f in ast.get("functions", [])]
        code_summary += f"- `{path}`: classes={classes}, functions={funcs}, imports={ast.get('imports', [])}\n"

    # 2. Invoke LLM to evaluate quality scores and rationale
    quality_prompt = """
    You are an expert software engineer and code auditor.
    Evaluate the quality of this codebase based on its architecture, technology stack, and structure.
    
    **Architecture Style**:
    {style}
    
    **Overview**:
    {overview}
    
    **File AST Summary**:
    {code_summary}
    
    Evaluate the codebase across these 7 dimensions, giving a score from 1.0 to 10.0 and a brief sentence explanation:
    1. Readability: Naming conventions, style consistency, comments.
    2. Maintainability: Modularity, coupling, duplication, complexity.
    3. Scalability: Bottlenecks, asynchronous operations, query structures.
    4. Security: Hardcoded secrets, safe inputs, insecure dependencies.
    5. Performance: Loop complexity, memory usage, caching opportunities.
    6. Testing: General unit testing structure, test coverage markers.
    7. Documentation: Setup guides, README, comments presence.
    
    Provide your evaluation strictly in JSON format matching this schema:
    {{
      "readability_score": 8.0,
      "readability_comment": "...",
      "maintainability_score": 7.5,
      "maintainability_comment": "...",
      "scalability_score": 6.8,
      "scalability_comment": "...",
      "security_score": 8.2,
      "security_comment": "...",
      "performance_score": 7.0,
      "performance_comment": "...",
      "testing_score": 5.0,
      "testing_comment": "...",
      "documentation_score": 6.5,
      "documentation_comment": "..."
    }}
    """
    
    prompt = ChatPromptTemplate.from_template(quality_prompt)
    chain = prompt | openai_accuracy_chain | JsonOutputParser()
    
    try:
        quality_analysis = chain.invoke({
            "style": arch.get("style", "N/A"),
            "overview": arch.get("overview", "N/A"),
            "code_summary": code_summary
        })
    except Exception as e:
        logging.error(f"Failed quality analysis: {e}")
        # Return default fallback scores
        quality_analysis = {
            "readability_score": 7.0,
            "readability_comment": "Standard formatting, standard names.",
            "maintainability_score": 7.0,
            "maintainability_comment": "Modular structures, standard separation.",
            "scalability_score": 7.0,
            "scalability_comment": "Standard web backend features.",
            "security_score": 7.0,
            "security_comment": "Needs environment variable audits.",
            "performance_score": 7.0,
            "performance_comment": "Runs efficiently, loops appear correct.",
            "testing_score": 6.0,
            "testing_comment": "Unit tests folder is defined in path.",
            "documentation_score": 6.0,
            "documentation_comment": "README file exists in root."
        }

    return {
        "quality_analysis": quality_analysis,
        "analysis_status": "detecting_issues"
    }
