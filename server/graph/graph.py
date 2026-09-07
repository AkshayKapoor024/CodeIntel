import sys
import os
import sqlite3
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from server.graph.state import GraphState
from server.graph.router import route_request, route_mode

# Analysis Nodes
from server.graph.nodes.analysis.repository import (
    analysis_validate_repository,
    analysis_clone_repository,
    analysis_repository_synthesizer,
    analysis_persist_analysis
)
from server.graph.nodes.analysis.inspection import (
    analysis_repository_inspector,
    analysis_file_classifier
)
from server.graph.nodes.analysis.parsing import analysis_source_parser
from server.graph.nodes.analysis.analysis import (
    analysis_file_analysis,
    analysis_issue_detector
)
from server.graph.nodes.analysis.architecture import analysis_architecture_analyzer
from server.graph.nodes.analysis.quality import (
    analysis_dependency_analyzer,
    analysis_quality_analyzer
)

# Chat Nodes
from server.graph.nodes.chat.retrieval import (
    chat_load_repository_context,
    chat_relevant_file_selector,
    chat_context_retriever
)
from server.graph.nodes.chat.chat import (
    chat_query_understanding,
    chat_targeted_code_analyzer,
    chat_reasoning_agent,
    chat_response_generator
)

from server.logger.logger import logging
from server.exception.exception import CustomException

# Path to checkpointer DB
CHECKPOINT_DB_PATH = "server/data/langgraph_checkpoints.db"
os.makedirs(os.path.dirname(CHECKPOINT_DB_PATH), exist_ok=True)

# Build the Single Graph
def graph_builder() -> StateGraph:
    try:
        logging.info("Started building Unified Single Graph...")
        workflow = StateGraph(GraphState)

        # 1. Add Router entry node
        workflow.add_node("router", route_request)

        # 2. Add Repository Analysis Nodes
        workflow.add_node("analysis_validate_repository", analysis_validate_repository)
        workflow.add_node("analysis_clone_repository", analysis_clone_repository)
        workflow.add_node("analysis_repository_inspector", analysis_repository_inspector)
        workflow.add_node("analysis_file_classifier", analysis_file_classifier)
        workflow.add_node("analysis_source_parser", analysis_source_parser)
        workflow.add_node("analysis_file_analysis", analysis_file_analysis)
        workflow.add_node("analysis_dependency_analyzer", analysis_dependency_analyzer)
        workflow.add_node("analysis_architecture_analyzer", analysis_architecture_analyzer)
        workflow.add_node("analysis_quality_analyzer", analysis_quality_analyzer)
        workflow.add_node("analysis_issue_detector", analysis_issue_detector)
        workflow.add_node("analysis_repository_synthesizer", analysis_repository_synthesizer)
        workflow.add_node("analysis_persist_analysis", analysis_persist_analysis)

        # 3. Add Conversational Chat Nodes
        workflow.add_node("chat_load_repository_context", chat_load_repository_context)
        workflow.add_node("chat_query_understanding", chat_query_understanding)
        workflow.add_node("chat_relevant_file_selector", chat_relevant_file_selector)
        workflow.add_node("chat_context_retriever", chat_context_retriever)
        workflow.add_node("chat_targeted_code_analyzer", chat_targeted_code_analyzer)
        workflow.add_node("chat_reasoning_agent", chat_reasoning_agent)
        workflow.add_node("chat_response_generator", chat_response_generator)

        # 4. Set Edges & Routing
        workflow.add_edge(START, "router")
        
        # Route depending on mode field
        workflow.add_conditional_edges(
            "router",
            route_mode,
            {
                "analyze": "analysis_validate_repository",
                "chat": "chat_load_repository_context"
            }
        )

        # Analysis path
        workflow.add_edge("analysis_validate_repository", "analysis_clone_repository")
        workflow.add_edge("analysis_clone_repository", "analysis_repository_inspector")
        workflow.add_edge("analysis_repository_inspector", "analysis_file_classifier")
        workflow.add_edge("analysis_file_classifier", "analysis_source_parser")
        workflow.add_edge("analysis_source_parser", "analysis_file_analysis")
        workflow.add_edge("analysis_file_analysis", "analysis_dependency_analyzer")
        workflow.add_edge("analysis_dependency_analyzer", "analysis_architecture_analyzer")
        workflow.add_edge("analysis_architecture_analyzer", "analysis_quality_analyzer")
        workflow.add_edge("analysis_quality_analyzer", "analysis_issue_detector")
        workflow.add_edge("analysis_issue_detector", "analysis_repository_synthesizer")
        workflow.add_edge("analysis_repository_synthesizer", "analysis_persist_analysis")
        workflow.add_edge("analysis_persist_analysis", END)

        # Conversational path
        workflow.add_edge("chat_load_repository_context", "chat_query_understanding")
        workflow.add_edge("chat_query_understanding", "chat_relevant_file_selector")
        workflow.add_edge("chat_relevant_file_selector", "chat_context_retriever")
        workflow.add_edge("chat_context_retriever", "chat_targeted_code_analyzer")
        workflow.add_edge("chat_targeted_code_analyzer", "chat_reasoning_agent")
        workflow.add_edge("chat_reasoning_agent", "chat_response_generator")
        workflow.add_edge("chat_response_generator", END)

        # 5. Compile with persistent thread-safe SQLite Checkpointer
        conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        checkpointer.setup()
        graph = workflow.compile(checkpointer=checkpointer)
        
        logging.info("Unified Single Graph compiled successfully with persistent SqliteSaver.")
        return graph

    except Exception as e:
        logging.error(f"Failed to build unified graph: {str(e)}")
        raise CustomException(e, sys)