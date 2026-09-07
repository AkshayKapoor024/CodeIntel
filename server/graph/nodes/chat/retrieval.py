import os
from typing import Dict, Any, List
from server.graph.state import GraphState
from server.database.sqlite_manager import SqliteManager
from server.services.github_service import GitHubService
from server.logger.logger import logging
from server.core.llms import openai_accuracy_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

DB_PATH = "server/data/codebase_intelligence.db"

def chat_load_repository_context(state: GraphState) -> Dict[str, Any]:
    """
    Chat Node 1: Loads the repository's metadata, directory tree, quality scores, 
    and file analyses from SQLite database.
    """
    logging.info("Running node: chat_load_repository_context")
    repo_id = state.get("repository_id")
    if not repo_id:
        return {"errors": ["No repository_id provided in state."]}
        
    db = SqliteManager(DB_PATH)
    repo = db.get_repository(repo_id)
    if not repo:
        return {"errors": [f"Repository with ID {repo_id} not found."]}
        
    files = db.get_files(repo_id)
    dependencies_list = db.get_dependencies(repo_id)
    issues = db.get_issues(repo_id)
    
    # Restructure file metadata, ASTs, and file summaries
    files_list = []
    file_metadata_dict = {}
    ast_data_dict = {}
    file_analysis_dict = {}
    
    for f in files:
        path = f["file_path"]
        files_list.append(path)
        file_metadata_dict[path] = {
            "type": f["file_type"],
            "size": f["file_size"]
        }
        ast_data_dict[path] = f["ast_data"] or {}
        file_analysis_dict[path] = f["analysis"] or {}
        
    # Restructure dependencies map
    dependencies_map = {}
    for dep in dependencies_list:
        src = dep["source_file"]
        tgt = dep["target_file"]
        dtype = dep["dependency_type"]
        if src not in dependencies_map:
            dependencies_map[src] = {}
        dependencies_map[src][tgt] = dtype
        
    arch = repo.get("architecture_analysis")
    arch_dict = {"overview": arch} if isinstance(arch, str) else (arch or {})

    # Inject loaded data into the state
    return {
        "repository_url": repo.get("github_url"),
        "branch": repo.get("branch"),
        "commit_hash": repo.get("commit_hash"),
        "directory_tree": repo.get("directory_map"),
        "files": files_list,
        "file_metadata": file_metadata_dict,
        "ast_data": ast_data_dict,
        "file_analysis": file_analysis_dict,
        "dependencies": dependencies_map,
        "architecture_analysis": arch_dict,
        "quality_analysis": repo.get("quality_analysis"),
        "issues": issues,
        "final_summary": repo.get("final_summary"),
        "final_report": repo.get("final_report"),
        "errors": []
    }

def chat_relevant_file_selector(state: GraphState) -> Dict[str, Any]:
    """
    Chat Node 3: Predicts and selects which files are actually relevant to the user query
    to optimize token costs.
    """
    logging.info("Running node: chat_relevant_file_selector")
    user_query = state.get("user_query")
    files = state.get("files") or []
    file_analysis = state.get("file_analysis") or {}
    
    if not user_query:
        # Get query from last message if user_query is not explicit
        messages = state.get("messages") or []
        if messages:
            user_query = messages[-1].content
            
    if not user_query or not files:
        return {"relevant_files": []}

    # Format file list with brief purposes
    file_summary_text = ""
    for path in files[:40]: # Send up to 40 candidate files
        purpose = file_analysis.get(path, {}).get("purpose", "N/A")
        file_summary_text += f"- `{path}`: {purpose}\n"

    selector_prompt = """
    You are an expert code navigation helper. Identify a MINIMAL set of files (maximum 5 files) 
    that are highly relevant to answering this user query.
    
    User Query: "{query}"
    
    Codebase Files:
    {file_summaries}
    
    Return your list strictly as a JSON array of strings containing the file paths.
    Example: ["services/auth.py", "models/user.py"]
    """
    
    prompt = ChatPromptTemplate.from_template(selector_prompt)
    chain = prompt | openai_accuracy_chain | JsonOutputParser()
    
    try:
        relevant_files = chain.invoke({
            "query": user_query,
            "file_summaries": file_summary_text
        })
        logging.info(f"Selector identified relevant files: {relevant_files}")
    except Exception as e:
        logging.error(f"Selector failed: {e}")
        # Fallback to search query matches or first file
        relevant_files = [f for f in files if os.path.basename(f).split('.')[0].lower() in user_query.lower()][:3]
        if not relevant_files and files:
            relevant_files = [files[0]]
            
    return {"relevant_files": relevant_files}

def chat_context_retriever(state: GraphState) -> Dict[str, Any]:
    """
    Chat Node 4: Fetches actual file source code from local cache or on-demand via GitHub API.
    """
    logging.info("Running node: chat_context_retriever")
    repo_id = state.get("repository_id", "")
    repo_url = state.get("repository_url", "")
    commit_hash = state.get("commit_hash", "")
    relevant_files = state.get("relevant_files") or []
    
    retrieved_context = []
    local_path = os.path.abspath(f"./server/temp_clones/{repo_id}")
    service = GitHubService()

    for f_path in relevant_files:
        code_found = None
        
        # 1. Check if local cloned workspace exists
        if local_path and os.path.exists(local_path):
            full_local_path = os.path.join(local_path, f_path)
            if os.path.exists(full_local_path):
                try:
                    with open(full_local_path, "r", encoding="utf-8", errors="ignore") as f:
                        code_found = f.read()
                    logging.info(f"Retrieved {f_path} from local workspace clone.")
                except Exception as e:
                    logging.warning(f"Could not read local file {f_path}: {e}")
                    
        # 2. On-demand GitHub API fetch if not found locally
        if code_found is None and repo_url:
            try:
                code_found = service.fetch_file_content_sync(repo_url, commit_hash, f_path)
                logging.info(f"Retrieved {f_path} via GitHub service.")
            except Exception as e:
                logging.error(f"Failed to fetch {f_path} from GitHub: {e}")
                code_found = f"// File {f_path} (could not be retrieved: {str(e)})"
                
        if code_found is None:
            code_found = f"// File {f_path} (no content available)"
            
        retrieved_context.append({"file": f_path, "code": code_found})
        
    return {"retrieved_context": retrieved_context}
