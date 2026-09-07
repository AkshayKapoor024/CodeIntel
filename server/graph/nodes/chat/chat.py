import json
import re
from typing import Dict, Any, List
from server.graph.state import GraphState
from server.logger.logger import logging
from server.core.llms import openai_accuracy_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

def chat_query_understanding(state: GraphState) -> Dict[str, Any]:
    """
    Chat Node 2: Classifies the intent of the incoming user query.
    Categories: General, File-specific, Architectural, Debugging, Security, Modification.
    """
    logging.info("Running node: chat_query_understanding")
    messages = state.get("messages") or []
    user_query = state.get("user_query")
    
    if not user_query and messages:
        user_query = messages[-1].content
        
    if not user_query:
        return {"query_type": "General"}

    classification_prompt = """
    Classify the intent of this user query about a software repository.
    Choose exactly one category from:
    - General: Overview, synopsis, or general repository questions (e.g. "What does this repo do?")
    - File-specific: Specific questions about a single file (e.g. "Explain auth.py")
    - Architectural: Overall structure, layout, modules interaction (e.g. "How does the backend authenticate?")
    - Debugging: Locating bugs, reasons for failures (e.g. "Why does my connection fail?")
    - Security: Potential vulnerabilities or compliance risks (e.g. "Are there SQL injections here?")
    - Modification: Implementing features, extensions (e.g. "How do I add a new route?")
    
    User Query: "{query}"
    
    Return only the category name as a plain string.
    """
    
    prompt = ChatPromptTemplate.from_template(classification_prompt)
    chain = prompt | openai_accuracy_chain | StrOutputParser()
    
    try:
        query_type = chain.invoke({"query": user_query}).strip()
        # Clean up output if any extra characters exist
        for cat in ["General", "File-specific", "Architectural", "Debugging", "Security", "Modification"]:
            if cat.lower() in query_type.lower():
                query_type = cat
                break
    except Exception as e:
        logging.error(f"Classification failed: {e}")
        query_type = "General"
        
    logging.info(f"Classified query category: {query_type}")
    return {"query_type": query_type, "user_query": user_query}

def chat_targeted_code_analyzer(state: GraphState) -> Dict[str, Any]:
    """
    Chat Node 5: Performs a targeted inspection of the retrieved source files 
    focusing on the user's specific question.
    """
    logging.info("Running node: chat_targeted_code_analyzer")
    user_query = state.get("user_query")
    retrieved_context = state.get("retrieved_context") or []
    
    if not retrieved_context or not user_query:
        return {"reasoning": "No relevant source files retrieved to analyze."}

    # Format retrieved code for context
    code_inputs = ""
    for ctx in retrieved_context:
        code_inputs += f"\n--- FILE: {ctx['file']} ---\n{ctx['code']}\n"

    analysis_prompt = """
    You are an expert code auditor. Analyze the following target source code files to answer the user's query.
    Extract key lines of code, trace control flow, and identify potential bugs or logic related to the query.
    
    User Query: "{query}"
    
    Source Code:
    {code_inputs}
    
    Write a concise summary of your targeted findings, noting key functions, parameters, or line numbers.
    """
    
    prompt = ChatPromptTemplate.from_template(analysis_prompt)
    chain = prompt | openai_accuracy_chain | StrOutputParser()
    
    try:
        findings = chain.invoke({"query": user_query, "code_inputs": code_inputs})
    except Exception as e:
        logging.error(f"Targeted analysis failed: {e}")
        findings = f"Targeted analysis summary based on available context for '{user_query}'."
        
    return {"reasoning": findings}

def chat_reasoning_agent(state: GraphState) -> Dict[str, Any]:
    """
    Chat Node 6: Integrates findings, code structure, AST, and conversation history
    to construct a comprehensive explanation.
    """
    logging.info("Running node: chat_reasoning_agent")
    user_query = state.get("user_query")
    query_type = state.get("query_type")
    relevant_files = state.get("relevant_files") or []
    reasoning_findings = state.get("reasoning") or ""
    
    # We build a final reasoning context for the response generator
    return {
        "reasoning": f"Query Type: {query_type}\nRelevant Files: {relevant_files}\nTargeted Findings:\n{reasoning_findings}"
    }

def chat_response_generator(state: GraphState) -> Dict[str, Any]:
    """
    Chat Node 7: Drafts the final conversational response, citing source file paths
    and line numbers where appropriate.
    """
    logging.info("Running node: chat_response_generator")
    user_query = state.get("user_query")
    reasoning = state.get("reasoning") or ""
    retrieved_context = state.get("retrieved_context") or []
    relevant_files = state.get("relevant_files") or []
    
    code_context_text = ""
    for ctx in retrieved_context:
        # Give lines prefix for LLM to cite
        lines = ctx["code"].splitlines()
        code_context_text += f"\n--- FILE: {ctx['file']} ---\n"
        for idx, line in enumerate(lines[:300]): # Limit to first 300 lines for prompt limits
            code_context_text += f"{idx + 1}: {line}\n"

    response_prompt = """
    You are an intelligent codebase assistant. Provide a precise, user-friendly answer to the query 
    based on the codebase context and previous reasoning.
    
    **Instructions**:
    1. Answer the query thoroughly, explaining the logic step-by-step.
    2. CITE specific file names and line numbers where the implementation resides.
    3. Make sure to structure code snippets using Markdown code blocks.
    
    User Query: "{query}"
    
    Reasoning Path:
    {reasoning}
    
    Source Code (with Line Numbers):
    {code_context}
    
    Provide your output in JSON format matching this schema:
    {{
      "answer": "Your complete conversational markdown response.",
      "citations": [
        {{
          "file": "path/to/file.py",
          "line": 42
        }}
      ]
    }}
    """
    
    prompt = ChatPromptTemplate.from_template(response_prompt)
    chain = prompt | openai_accuracy_chain | JsonOutputParser()
    
    try:
        res = chain.invoke({
            "query": user_query,
            "reasoning": reasoning,
            "code_context": code_context_text
        })
        answer = res.get("answer", "")
        citations = res.get("citations", [])
    except Exception as e:
        logging.error(f"Response generation failed: {e}")
        # Direct fallback text
        answer = f"I've analyzed the files: {', '.join(relevant_files) if relevant_files else 'N/A'}.\n\n### Findings:\n{reasoning}"
        citations = []
        # Try to parse any file paths from relevant files as citations
        for f in relevant_files:
            citations.append({"file": f, "line": 1})

    return {
        "answer": answer,
        "citations": citations
    }
