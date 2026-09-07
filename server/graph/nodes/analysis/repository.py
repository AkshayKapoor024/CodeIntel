import os
import uuid
from typing import Dict, Any, List
from server.graph.state import GraphState
from server.services.github_service import GitHubService
from server.database.sqlite_manager import SqliteManager
from server.logger.logger import logging

# SQLite DB Path configuration
DB_PATH = "server/data/codebase_intelligence.db"

def analysis_validate_repository(state: GraphState) -> Dict[str, Any]:
    """
    Node 1: Validates GitHub URL and configures repo attributes.
    """
    logging.info("Running node: analysis_validate_repository")
    url = state.get("repository_url") or state.get("github_url")
    if not url:
        return {"errors": ["No GitHub URL provided in state."]}
    
    url = url.strip()
    if not url.startswith("https://github.com/"):
        return {"errors": ["Invalid GitHub URL. Must start with https://github.com/"]}

    parts = url.replace("https://github.com/", "").strip("/").split("/")
    if len(parts) < 2:
        return {"errors": ["Invalid repository URL format."]}

    owner = parts[0]
    repo = parts[1].split(".git")[0]
    branch = state.get("branch") or "main"
    
    # Generate unique repository ID if not exists
    repository_id = state.get("repository_id") or f"{owner}_{repo}"
    
    # Set status to cloning
    db = SqliteManager(DB_PATH)
    db.insert_repository(repository_id, url, branch, "")
    db.update_repository_status(repository_id, "cloning")

    return {
        "repository_id": repository_id,
        "repository_url": url,
        "branch": branch,
        "analysis_status": "cloning",
        "errors": []
    }

def analysis_clone_repository(state: GraphState) -> Dict[str, Any]:
    """
    Node 2: Clones the repository to a temporary workspace.
    """
    logging.info("Running node: analysis_clone_repository")
    repo_id = state["repository_id"]
    repo_url = state["repository_url"]
    branch = state.get("branch") or "main"
    
    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "cloning")

    # Local workspace path
    dest_path = os.path.abspath(f"./server/temp_clones/{repo_id}")
    
    try:
        service = GitHubService()
        commit_hash = service.clone_repository(repo_url, branch, dest_path)
        
        # Save commit hash in SQLite
        db.insert_repository(repo_id, repo_url, branch, commit_hash)
        db.update_repository_status(repo_id, "inspecting")
        
        return {
            "repository_path": dest_path,
            "commit_hash": commit_hash,
            "analysis_status": "inspecting",
            "errors": []
        }
    except Exception as e:
        logging.error(f"Clone failed: {e}")
        db.update_repository_status(repo_id, "failed")
        return {"errors": [f"Clone failed: {str(e)}"], "analysis_status": "failed"}

def analysis_repository_synthesizer(state: GraphState) -> Dict[str, Any]:
    """
    Node 11: Synthesizes individual file analyses into a final comprehensive Markdown report.
    """
    logging.info("Running node: analysis_repository_synthesizer")
    repo_id = state["repository_id"]
    
    db = SqliteManager(DB_PATH)
    db.update_repository_status(repo_id, "synthesizing")
    
    # Combine stats
    files = state.get("files") or []
    quality = state.get("quality_analysis") or {}
    issues = state.get("issues") or []
    arch = state.get("architecture_analysis") or {}
    
    arch_style = arch.get("style", "General Codebase") if isinstance(arch, dict) else "General Codebase"
    
    # General overview summary
    final_summary = (
        f"# Repository Overview: {repo_id}\n\n"
        f"**GitHub URL:** {state.get('repository_url')}\n"
        f"**Branch:** {state.get('branch')}\n"
        f"**Commit SHA:** {state.get('commit_hash')}\n"
        f"**Total Files Indexed:** {len(files)}\n\n"
        f"## Architecture Style\n"
        f"{arch_style}\n\n"
        f"## Quality Evaluation\n"
        f"- **Readability Score:** {quality.get('readability_score', 'N/A')}/10\n"
        f"- **Maintainability Score:** {quality.get('maintainability_score', 'N/A')}/10\n"
        f"- **Scalability Score:** {quality.get('scalability_score', 'N/A')}/10\n"
        f"- **Security Score:** {quality.get('security_score', 'N/A')}/10\n"
        f"- **Performance Score:** {quality.get('performance_score', 'N/A')}/10\n"
        f"- **Testing Score:** {quality.get('testing_score', 'N/A')}/10\n"
        f"- **Documentation Score:** {quality.get('documentation_score', 'N/A')}/10\n\n"
        f"## Major Issues Found ({len(issues)} Issues)\n"
    )
    
    for issue in issues:
        final_summary += f"- **[{issue.get('severity', 'LOW')}]** in `{issue.get('file_path')}`: {issue.get('problem')}\n"
        
    final_summary += f"\n## Technology Stack\n"
    tech_stack = arch.get("technology_stack", {}) if isinstance(arch, dict) else {}
    for lang, count in tech_stack.items():
        final_summary += f"- {lang}: {count} files\n"
        
    # Build complete report object
    final_report = {
        "overview": final_summary,
        "directory_tree": state.get("directory_tree"),
        "quality_scores": quality,
        "issues": issues,
        "architecture": arch,
        "recommendations": state.get("recommendations") or []
    }
    
    return {
        "final_summary": final_summary,
        "final_report": final_report,
        "analysis_status": "synthesizing"
    }

def analysis_persist_analysis(state: GraphState) -> Dict[str, Any]:
    """
    Node 12: Persists the entire analysis state into the SQLite database.
    """
    logging.info("Running node: analysis_persist_analysis")
    repo_id = state["repository_id"]
    db = SqliteManager(DB_PATH)
    
    arch = state.get("architecture_analysis") or {}
    arch_overview = arch.get("overview", "N/A") if isinstance(arch, dict) else str(arch)

    # 1. Update Repository Summary & Report
    db.update_repository_analysis(
        repo_id=repo_id,
        directory_map=state.get("directory_map") or state.get("directory_tree") or {},
        architecture_analysis=arch_overview,
        quality_analysis=state.get("quality_analysis") or {},
        final_summary=state.get("final_summary") or "",
        final_report=state.get("final_report") or {}
    )
    
    # 2. Insert Files & ASTs & Summaries
    files = state.get("files") or []
    file_metadata = state.get("file_metadata") or {}
    ast_data = state.get("ast_data") or {}
    file_analysis = state.get("file_analysis") or {}
    
    for f_path in files:
        meta = file_metadata.get(f_path, {})
        f_type = meta.get("type", "unknown")
        f_size = meta.get("size", 0)
        ast = ast_data.get(f_path, {})
        an = file_analysis.get(f_path, {})
        db.insert_file(repo_id, f_path, f_type, f_size, ast, an)
        
    # 3. Insert Dependencies
    deps = state.get("dependencies") or {}
    for src, targets in deps.items():
        if isinstance(targets, list):
            for tgt in targets:
                if isinstance(tgt, dict):
                    db.insert_dependency(repo_id, src, tgt.get("file", ""), tgt.get("type", "import"))
                else:
                    db.insert_dependency(repo_id, src, str(tgt), "import")
        elif isinstance(targets, dict):
            for tgt_file, dep_type in targets.items():
                db.insert_dependency(repo_id, src, tgt_file, dep_type)

    # 4. Insert Issues
    issues = state.get("issues") or []
    for issue in issues:
        issue_id = issue.get("id") or str(uuid.uuid4())
        db.insert_issue(
            issue_id=issue_id,
            repo_id=repo_id,
            file_path=issue.get("file_path"),
            line=issue.get("line", 1),
            severity=issue.get("severity", "LOW"),
            category=issue.get("category", "General"),
            problem=issue.get("problem", ""),
            impact=issue.get("impact", ""),
            recommendation=issue.get("recommendation", ""),
            confidence=issue.get("confidence", 1.0)
        )
        
    # Mark status as completed
    db.update_repository_status(repo_id, "completed")
    logging.info(f"Analysis successfully persisted for repository: {repo_id}")
    
    # Clean up temporary cloned folder to save disk space
    repo_path = state.get("repository_path")
    if repo_path and os.path.exists(repo_path):
        import shutil
        shutil.rmtree(repo_path, ignore_errors=True)
        logging.info(f"Cleaned up temporary cloned folder: {repo_path}")

    return {
        "analysis_status": "completed"
    }
