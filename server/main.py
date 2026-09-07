import os
import sys
import uuid
import certifi
import json
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any

from pydantic import BaseModel
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from bson import ObjectId
from uvicorn import run as app_run

from server.logger.logger import logging
from server.graph.graph import graph_builder
from server.graph.state import GraphState
from server.database.sqlite_manager import SqliteManager
from server.core.mongo import users, sessions, chat_history
from server.tools.password_hashing import hash_password, verify_password
from server.services.github_service import GitHubService
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()
certifi.where()

SESSION_KEY = os.getenv("SESSION_SECRET_KEY", "super-secret-codeintel-session-key")
DB_PATH = "server/data/codebase_intelligence.db"

app = FastAPI(title="Intelligent Codebase Analysis & Exploration API")

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_KEY,
    session_cookie="codeintel_session",
    max_age=3600 * 24  # 24 hours
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize single LangGraph
try:
    logging.info("Initializing LangGraph Unified Single Graph workflow...")
    graph = graph_builder()
except Exception as e:
    logging.error(f"Failed to build graph: {str(e)}")
    raise e

# Database Helper
def get_db():
    return SqliteManager(DB_PATH)

# Request schemas
class CreateRepoRequest(BaseModel):
    github_url: str
    branch: Optional[str] = "main"

class MessageRequest(BaseModel):
    message: str

class UserRegisterRequest(BaseModel):
    name: str
    username: str
    email: str
    password: str

class UserLoginRequest(BaseModel):
    email: str
    password: str

# Helper to verify auth
def get_logged_in_user_id(request: Request) -> str:
    user_id = request.session.get("user")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user_id

# Background worker task for Graph A analysis
def run_analysis_in_background(repo_id: str, github_url: str, branch: str):
    logging.info(f"Starting background repo analysis task for {repo_id}")
    config = {"configurable": {"thread_id": repo_id}}
    state = {
        "mode": "analyze",
        "repository_id": repo_id,
        "repository_url": github_url,
        "github_url": github_url,
        "branch": branch,
        "analysis_status": "cloning",
        "errors": []
    }
    try:
        graph.invoke(state, config=config)
        logging.info(f"Background repo analysis completed successfully for {repo_id}")
    except Exception as e:
        logging.error(f"Background repo analysis failed for {repo_id}: {e}")
        db = SqliteManager(DB_PATH)
        db.update_repository_status(repo_id, "failed")

# Root Endpoint
@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.post("/api/auth/register", tags=["Authentication"])
async def register(request: Request, user_req: UserRegisterRequest):
    try:
        if users.find_one({"email": user_req.email}):
            return JSONResponse(content={"error": "User already exists with this email"}, status_code=400)
        
        hashed = hash_password(password=user_req.password)
        res = users.insert_one({
            "name": user_req.name,
            "username": user_req.username,
            "email": user_req.email,
            "password": hashed,
            "chat_histories": []
        })
        
        # Login automatically
        request.session["user"] = str(res.inserted_id)
        return JSONResponse(content={
            "message": "User signup successful",
            "user": {
                "name": user_req.name,
                "email": user_req.email,
                "username": user_req.username
            }
        }, status_code=200)
    except Exception as e:
        logging.error(f"Signup error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/auth/login", tags=["Authentication"])
async def login(request: Request, login_req: UserLoginRequest):
    try:
        db_user = users.find_one({"email": login_req.email})
        if not db_user:
            return JSONResponse(content={"error": "User does not exist"}, status_code=400)
            
        if not verify_password(plain=login_req.password, hashed=db_user["password"]):
            return JSONResponse(content={"error": "Password did not match"}, status_code=400)
            
        request.session["user"] = str(db_user["_id"])
        return JSONResponse(content={
            "message": "User login successful",
            "user": {
                "name": db_user["name"],
                "email": db_user["email"],
                "username": db_user["username"]
            }
        }, status_code=200)
    except Exception as e:
        logging.error(f"Login error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/auth/logout", tags=["Authentication"])
async def logout(request: Request):
    request.session.clear()
    return JSONResponse(content={"message": "Logged out successfully"}, status_code=200)

@app.get("/api/auth/me", tags=["Authentication"])
async def me(request: Request):
    user_id = request.session.get("user")
    if not user_id:
        return JSONResponse(content={"authenticated": False}, status_code=401)
        
    db_user = users.find_one({"_id": ObjectId(user_id)})
    if not db_user:
        request.session.clear()
        return JSONResponse(content={"authenticated": False}, status_code=401)
        
    return JSONResponse(content={
        "authenticated": True,
        "user": {
            "name": db_user["name"],
            "email": db_user["email"],
            "username": db_user["username"]
        }
    }, status_code=200)

# ==========================================
# REPOSITORY ROUTES
# ==========================================

@app.post("/api/repositories", tags=["Repositories"])
async def create_repository(request: Request, repo_req: CreateRepoRequest, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    url = repo_req.github_url.strip()
    
    parts = url.replace("https://github.com/", "").strip("/").split("/")
    if len(parts) < 2:
        return JSONResponse(content={"error": "Invalid GitHub URL"}, status_code=400)
        
    owner = parts[0]
    repo = parts[1].split(".git")[0]
    repo_id = f"{owner}_{repo}"
    branch = repo_req.branch or "main"
    
    db.insert_repository(repo_id, url, branch, "")
    db.update_repository_status(repo_id, "cloned_registered")
    
    return JSONResponse(content={
        "repository_id": repo_id,
        "status": "cloned_registered"
    }, status_code=200)

@app.get("/api/repositories", tags=["Repositories"])
async def get_repositories(request: Request, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    repos = db.list_repositories()
    return JSONResponse(content={"repositories": repos}, status_code=200)

@app.get("/api/repositories/{repository_id}", tags=["Repositories"])
async def get_repository(repository_id: str, request: Request, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    repo = db.get_repository(repository_id)
    if not repo:
        return JSONResponse(content={"error": "Repository not found"}, status_code=404)
    return JSONResponse(content={"repository": repo}, status_code=200)

@app.delete("/api/repositories/{repository_id}", tags=["Repositories"])
async def delete_repository(repository_id: str, request: Request, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    success = db.delete_repository(repository_id)
    if not success:
        return JSONResponse(content={"error": "Failed to delete repository"}, status_code=400)
    return JSONResponse(content={"message": "Repository deleted successfully"}, status_code=200)

# ==========================================
# QUALITY ANALYSIS ROUTES
# ==========================================

@app.post("/api/repositories/{repository_id}/analyze", tags=["Analysis"])
async def analyze_repository(repository_id: str, request: Request, background_tasks: BackgroundTasks, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    repo = db.get_repository(repository_id)
    if not repo:
        return JSONResponse(content={"error": "Repository not found"}, status_code=404)
        
    db.update_repository_status(repository_id, "cloning")
    
    # Spawn background worker
    background_tasks.add_task(
        run_analysis_in_background,
        repo_id=repository_id,
        github_url=repo["github_url"],
        branch=repo["branch"]
    )
    
    return JSONResponse(content={
        "repository_id": repository_id,
        "status": "analysis_started"
    }, status_code=200)

@app.get("/api/repositories/{repository_id}/status", tags=["Analysis"])
async def get_analysis_status(repository_id: str, request: Request, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    repo = db.get_repository(repository_id)
    if not repo:
        return JSONResponse(content={"error": "Repository not found"}, status_code=404)
    return JSONResponse(content={"status": repo["status"]}, status_code=200)

@app.get("/api/repositories/{repository_id}/analysis", tags=["Analysis"])
async def get_analysis_results(repository_id: str, request: Request, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    repo = db.get_repository(repository_id)
    if not repo:
        return JSONResponse(content={"error": "Repository not found"}, status_code=404)
        
    files = db.get_files(repository_id)
    return JSONResponse(content={
        "repository": repo,
        "files_count": len(files),
        "quality_scores": repo.get("quality_analysis")
    }, status_code=200)

@app.get("/api/repositories/{repository_id}/report", tags=["Analysis"])
async def get_analysis_report(repository_id: str, request: Request, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    repo = db.get_repository(repository_id)
    if not repo:
        return JSONResponse(content={"error": "Repository not found"}, status_code=404)
    return JSONResponse(content={
        "report": repo.get("final_report"),
        "summary": repo.get("final_summary")
    }, status_code=200)

@app.get("/api/repositories/{repository_id}/structure", tags=["Analysis"])
async def get_analysis_structure(repository_id: str, request: Request, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    repo = db.get_repository(repository_id)
    if not repo:
        return JSONResponse(content={"error": "Repository not found"}, status_code=404)
    return JSONResponse(content={"directory_tree": repo.get("directory_map")}, status_code=200)

@app.get("/api/repositories/{repository_id}/issues", tags=["Analysis"])
async def get_analysis_issues(repository_id: str, request: Request, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    issues_list = db.get_issues(repository_id)
    return JSONResponse(content={"issues": issues_list}, status_code=200)

@app.get("/api/repositories/{repository_id}/files/{file_path:path}", tags=["Analysis"])
async def get_repository_file(repository_id: str, file_path: str, request: Request, db: SqliteManager = Depends(get_db)):
    get_logged_in_user_id(request)
    repo = db.get_repository(repository_id)
    if not repo:
        return JSONResponse(content={"error": "Repository not found"}, status_code=404)
        
    file_info = db.get_file(repository_id, file_path)
    
    # Try fetching content from local temp folder or GitHub API
    content = None
    local_path = os.path.abspath(f"./server/temp_clones/{repository_id}/{file_path}")
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            pass
            
    if content is None and repo.get("github_url"):
        try:
            service = GitHubService()
            content = service.fetch_file_content_sync(repo["github_url"], repo.get("commit_hash", "main"), file_path)
        except Exception as e:
            content = f"// Unable to fetch file content: {str(e)}"
            
    return JSONResponse(content={
        "file_path": file_path,
        "file_info": file_info,
        "content": content
    }, status_code=200)

# ==========================================
# CONVERSATIONAL CHAT ROUTES
# ==========================================

@app.post("/api/repositories/{repository_id}/conversations", tags=["Chat"])
async def create_conversation(repository_id: str, request: Request, db: SqliteManager = Depends(get_db)):
    user_id = get_logged_in_user_id(request)
    repo = db.get_repository(repository_id)
    if not repo:
        return JSONResponse(content={"error": "Repository not found"}, status_code=404)
        
    now = datetime.now(UTC)
    chat_doc = {
        "user_id": user_id,
        "repository_id": repository_id,
        "title": f"Chat about {repository_id}",
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }
    
    res = chat_history.insert_one(chat_doc)
    chat_id = str(res.inserted_id)
    
    users.update_one(
        {"_id": ObjectId(user_id)},
        {"$push": {"chat_histories": chat_id}}
    )
    
    return JSONResponse(content={
        "conversation_id": chat_id,
        "title": chat_doc["title"]
    }, status_code=200)

@app.get("/api/repositories/{repository_id}/conversations", tags=["Chat"])
async def get_conversations(repository_id: str, request: Request):
    user_id = get_logged_in_user_id(request)
    chats = chat_history.find({"user_id": user_id, "repository_id": repository_id}).sort("updated_at", -1)
    res_list = [{"conversation_id": str(c["_id"]), "title": c.get("title", "Conversation"), "updated_at": str(c.get("updated_at", ""))} for c in chats]
    return JSONResponse(content={"conversations": res_list}, status_code=200)

@app.get("/api/conversations/{conversation_id}", tags=["Chat"])
async def get_conversation(conversation_id: str, request: Request):
    user_id = get_logged_in_user_id(request)
    try:
        chat = chat_history.find_one({"_id": ObjectId(conversation_id), "user_id": user_id})
    except Exception:
        return JSONResponse(content={"error": "Invalid conversation ID"}, status_code=400)
        
    if not chat:
        return JSONResponse(content={"error": "Conversation not found"}, status_code=404)
        
    chat["_id"] = str(chat["_id"])
    chat["created_at"] = str(chat.get("created_at", ""))
    chat["updated_at"] = str(chat.get("updated_at", ""))
    for msg in chat.get("messages", []):
        if "created_at" in msg:
            msg["created_at"] = str(msg["created_at"])
            
    return JSONResponse(content={"conversation": chat}, status_code=200)

@app.delete("/api/conversations/{conversation_id}", tags=["Chat"])
async def delete_conversation(conversation_id: str, request: Request):
    user_id = get_logged_in_user_id(request)
    try:
        res = chat_history.delete_one({"_id": ObjectId(conversation_id), "user_id": user_id})
    except Exception:
        return JSONResponse(content={"error": "Invalid conversation ID"}, status_code=400)
        
    if res.deleted_count == 0:
        return JSONResponse(content={"error": "Failed to delete conversation"}, status_code=400)
        
    users.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"chat_histories": conversation_id}}
    )
    return JSONResponse(content={"message": "Conversation deleted successfully"}, status_code=200)

@app.post("/api/conversations/{conversation_id}/messages", tags=["Chat"])
async def send_message(conversation_id: str, request: Request, msg_req: MessageRequest):
    user_id = get_logged_in_user_id(request)
    
    # 1. Fetch conversation history from MongoDB
    try:
        chat = chat_history.find_one({"_id": ObjectId(conversation_id), "user_id": user_id})
    except Exception:
        return JSONResponse(content={"error": "Invalid conversation ID"}, status_code=400)
        
    if not chat:
        return JSONResponse(content={"error": "Conversation not found"}, status_code=404)
        
    repo_id = chat["repository_id"]
    query = msg_req.message.strip()
    if not query:
        return JSONResponse(content={"error": "Message cannot be empty"}, status_code=400)
    
    # 2. Build conversational history elements in LangGraph format
    graph_messages = []
    for msg in chat.get("messages", []):
        if msg.get("role") == "human":
            graph_messages.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            graph_messages.append(AIMessage(content=msg.get("content", "")))
            
    # Include latest query
    graph_messages.append(HumanMessage(content=query))
    
    # 3. Invoke LangGraph chat path
    config = {"configurable": {"thread_id": conversation_id}}
    state = {
        "mode": "chat",
        "repository_id": repo_id,
        "conversation_id": conversation_id,
        "user_query": query,
        "messages": graph_messages,
        "errors": []
    }
    
    try:
        response = graph.invoke(state, config=config)
        answer = response.get("answer", "No response generated by assistant.")
        citations = response.get("citations", [])
    except Exception as e:
        logging.error(f"Chat execution failed: {e}")
        return JSONResponse(content={"error": f"Failed to run chat agent: {str(e)}"}, status_code=500)
        
    # 4. Save message pair in MongoDB
    now = datetime.now(UTC)
    messages_to_store = [
        {
            "role": "human",
            "content": query,
            "created_at": now
        },
        {
            "role": "assistant",
            "content": answer,
            "citations": citations,
            "created_at": now
        }
    ]
    
    # Generate automatic smart title from first query if default title
    update_fields = {
        "updated_at": now
    }
    if chat.get("title", "").startswith("Chat about ") and len(chat.get("messages", [])) == 0:
        short_title = query[:40] + ("..." if len(query) > 40 else "")
        update_fields["title"] = short_title
    
    chat_history.update_one(
        {"_id": ObjectId(conversation_id)},
        {
            "$push": {"messages": {"$each": messages_to_store}},
            "$set": update_fields
        }
    )
    
    return JSONResponse(content={
        "answer": answer,
        "references": citations
    }, status_code=200)

if __name__ == "__main__":
    app_run(app, host="0.0.0.0", port=8080)