"""
Routing edges for the Unified CodeIntel Graph.
Conditional dispatch functions and router helpers.
"""

from typing import Dict, Any
from server.graph.state import GraphState

def continue_to_mode(state: GraphState) -> str:
    """Returns the mode string ('analyze' or 'chat') to dispatch across branches."""
    return state.get("mode", "chat")