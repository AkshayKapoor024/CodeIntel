from typing import TypedDict, Annotated, List, Optional, Any
import operator
from langgraph.graph.message import add_messages

# Unified GraphState representing the single-graph design (Version 2.0)
class GraphState(TypedDict):
    # -- routing --
    mode: str  # "analyze" | "chat"

    # -- repository analysis fields (populated when mode == "analyze") --
    repository_id: str
    repository_url: Optional[str]
    branch: Optional[str]
    commit_hash: Optional[str]
    repository_path: Optional[str]
    directory_tree: Optional[dict]
    files: Optional[list]
    file_metadata: Optional[dict]
    ast_data: Optional[dict]
    file_analysis: Optional[dict]
    dependencies: Optional[dict]
    architecture_analysis: Optional[dict]
    quality_analysis: Optional[dict]
    maintainability_analysis: Optional[dict]
    scalability_analysis: Optional[dict]
    security_analysis: Optional[dict]
    issues: Optional[list]
    recommendations: Optional[list]
    final_summary: Optional[str]
    final_report: Optional[dict]
    analysis_status: Optional[str]

    # -- conversational fields (populated when mode == "chat") --
    conversation_id: Optional[str]
    messages: Annotated[list, add_messages]
    user_query: Optional[str]
    query_type: Optional[str]
    relevant_files: Optional[list]
    relevant_symbols: Optional[list]
    retrieved_context: Optional[list]
    reasoning: Optional[str]
    answer: Optional[str]
    citations: Optional[list]

    # -- shared --
    errors: list