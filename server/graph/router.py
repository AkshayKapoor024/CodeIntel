from typing import Dict, Any
from server.graph.state import GraphState
from server.logger.logger import logging

def route_request(state: GraphState) -> Dict[str, Any]:
    """
    Deterministic router node that decides whether the incoming request 
    should trigger repository analysis or conversational chat based on state shape.
    """
    logging.info("Routing request...")
    
    # 1. Explicit mode set in state
    explicit_mode = state.get("mode")
    if explicit_mode in ["analyze", "chat"]:
        logging.info(f"Routed request to explicit mode: {explicit_mode}")
        return {"mode": explicit_mode}
        
    github_url = state.get("github_url") or state.get("repository_url")
    conv_id = state.get("conversation_id")
    user_query = state.get("user_query")
    analysis_status = state.get("analysis_status")
    
    # 2. Conversational chat indicators
    if conv_id or user_query or (state.get("messages") and len(state["messages"]) > 0):
        mode = "chat"
    # 3. Active analysis indicators
    elif analysis_status in ["cloning", "inspecting", "parsing", "analyzing", "analyzing_files", "analyzing_architecture", "quality_check", "detecting_issues", "synthesizing"]:
        mode = "analyze"
    # 4. GitHub URL provided for initial analysis
    elif github_url:
        mode = "analyze"
    else:
        # Graceful fallback to chat
        mode = "chat"
        
    logging.info(f"Routed request to determined mode: {mode}")
    return {"mode": mode}

def route_mode(state: GraphState) -> str:
    """Helper condition to select path after router node."""
    return state.get("mode", "chat")
