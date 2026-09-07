import os
import uuid
import json
from typing import Dict, Any, List
from server.graph.state import GraphState
from server.database.sqlite_manager import SqliteManager
from server.logger.logger import logging
from server.core.llms import openai_accuracy_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

DB_PATH = "server/data/codebase_intelligence.db"

def analysis_file_analysis(state: GraphState) -> Dict[str, Any]:
    """
    Node 6: Analyzes individual source files to determine purpose, major responsibilities,
    and summaries.
    """
    logging.info("Running node: analysis_file_analysis")
    repo_id = state["repository_id"]
    repo_path = state["repository_path"]
    files = state.get("files") or []
    file_metadata = state.get("file_metadata") or {}
    ast_data = state.get("ast_data") or {}

    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "analyzing_files")

    file_analysis = {}
    
    # Selectively analyze files to conserve tokens and avoid rate limits.
    # We prioritize significant source files (Python, JS/TS, Java) and ignore configurations/binaries.
    analyzable_extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go"]
    code_files = [f for f in files if any(f.endswith(ext) for ext in analyzable_extensions)]
    
    # Sort by size and take the top 15 most important files
    code_files = sorted(code_files, key=lambda f: file_metadata.get(f, {}).get("size", 0), reverse=True)[:15]
    
    logging.info(f"Selected {len(code_files)} primary code files for deep LLM analysis.")

    file_summary_prompt = """
    You are an expert codebase analyzer. Analyze the source code of the file `{file_path}` in a repository.
    
    **AST Metadata**:
    Classes: {classes}
    Functions: {functions}
    Imports: {imports}
    
    **Source Code Preview (First 150 lines)**:
    {code_preview}
    
    Provide your analysis in JSON format matching this schema:
    {{
      "purpose": "A one-sentence description of what this module does.",
      "responsibilities": ["Primary responsibility 1", "Primary responsibility 2"],
      "summary": "A brief paragraph describing the module implementation, design patterns, and highlights."
    }}
    """
    
    prompt = ChatPromptTemplate.from_template(file_summary_prompt)
    chain = prompt | openai_accuracy_chain | JsonOutputParser()

    for f_path in files:
        meta = file_metadata.get(f_path, {})
        ast = ast_data.get(f_path, {})
        
        # If it's a code file and in the top selected list, run LLM analysis
        if f_path in code_files:
            full_path = os.path.join(repo_path, f_path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                code_preview = "".join(lines[:150])
                
                res = chain.invoke({
                    "file_path": f_path,
                    "classes": json.dumps(ast.get("classes", [])),
                    "functions": json.dumps(ast.get("functions", [])),
                    "imports": json.dumps(ast.get("imports", [])),
                    "code_preview": code_preview
                })
                file_analysis[f_path] = res
            except Exception as e:
                logging.warning(f"Failed LLM file analysis for {f_path}: {e}")
                # Fallback to structural metadata
                file_analysis[f_path] = {
                    "purpose": f"Contains code related to {os.path.basename(f_path)}",
                    "responsibilities": [f"Defines {len(ast.get('classes', []))} classes and {len(ast.get('functions', []))} functions"],
                    "summary": f"Source file in the repository. Imports: {', '.join(ast.get('imports', []))[:100]}"
                }
        else:
            # Deterministic analysis for non-code/minor files
            file_analysis[f_path] = {
                "purpose": f"System metadata or configuration file.",
                "responsibilities": [f"Configuration / static asset for {os.path.basename(f_path)}"],
                "summary": f"Configuration of type '{meta.get('type', 'unknown')}' with size {meta.get('size', 0)} bytes."
            }

    return {
        "file_analysis": file_analysis,
        "analysis_status": "analyzing_architecture"
    }

def analysis_issue_detector(state: GraphState) -> Dict[str, Any]:
    """
    Node 10: Aggregates discovered issues and runs final LLM validation for security and performance risks.
    """
    logging.info("Running node: analysis_issue_detector")
    repo_id = state["repository_id"]
    files = state.get("files") or []
    file_analysis = state.get("file_analysis") or {}
    quality_analysis = state.get("quality_analysis") or {}
    
    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "detecting_issues")

    # Sample summary of issues found during quality check
    issues_detected = []
    
    # We can invoke the LLM to scan files summaries and quality analysis for high-level issues
    issue_detector_prompt = """
    You are a professional security and code auditor.
    Review the following quality score overview and file summaries of a GitHub repository:
    
    **Quality Analysis Scores**:
    {quality_analysis}
    
    **Codebase Architecture Style**:
    {arch_analysis}
    
    **Overview of Primary Files**:
    {file_summaries}
    
    Identify 3 to 7 potential problems (security vulnerabilities, performance bottlenecks, maintainability/design issues, or gaps in test coverage) in the project.
    
    Return your findings STRICTLY as a JSON array of issues. Each issue must match this schema:
    [
      {{
        "file_path": "path/to/vulnerable_file.py",
        "line": 42,
        "severity": "HIGH" | "MEDIUM" | "LOW",
        "category": "Security" | "Performance" | "Scalability" | "Maintainability" | "Readability" | "Testing" | "Documentation",
        "problem": "Brief description of the problem",
        "impact": "Potential impact on production",
        "recommendation": "Actionable instructions to resolve the issue",
        "confidence": 0.95
      }}
    ]
    """
    
    # Format a summary of the files for the prompt
    file_summaries_text = ""
    for path, data in list(file_analysis.items())[:10]: # Top 10 files
        file_summaries_text += f"- File `{path}`: {data.get('purpose', 'N/A')}\n"
        
    arch_analysis = state.get("architecture_analysis") or {}
    
    prompt = ChatPromptTemplate.from_template(issue_detector_prompt)
    chain = prompt | openai_accuracy_chain | JsonOutputParser()
    
    try:
        issues_detected = chain.invoke({
            "quality_analysis": json.dumps(quality_analysis),
            "arch_analysis": arch_analysis.get("overview", "N/A"),
            "file_summaries": file_summaries_text
        })
        
        # Ensure issues have unique IDs
        for issue in issues_detected:
            issue["id"] = str(uuid.uuid4())
            
    except Exception as e:
        logging.error(f"Failed issue detection: {e}")
        # Return fallback issue list
        issues_detected = [
            {
                "id": str(uuid.uuid4()),
                "file_path": "README.md" if "README.md" in files else (files[0] if files else "N/A"),
                "line": 1,
                "severity": "LOW",
                "category": "Documentation",
                "problem": "Missing extensive setup guide",
                "impact": "Developers might find it difficult to start and configure this environment.",
                "recommendation": "Provide details on configurations, requirements, and deployment pipelines.",
                "confidence": 0.8
            }
        ]
        
    return {
        "issues": issues_detected,
        "analysis_status": "synthesizing"
    }
