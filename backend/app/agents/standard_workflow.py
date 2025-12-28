from typing import Dict, Any, AsyncGenerator
from loguru import logger
import json
import uuid
import asyncio

from app.orchestration.statechart_engine import StateGraph, WorkflowState, GraphEventType, GraphEvent
from app.services.llm_service import llm_service
from app.services.galaxy_service import GalaxyService
from app.orchestration.prompts import build_system_prompt
from app.orchestration.executor import ToolExecutor
from app.gen.agent.v1 import agent_service_pb2

# ==========================================
# Nodes
# ==========================================

async def context_builder_node(state: WorkflowState) -> WorkflowState:
    """Build user and conversation context."""
    logger.info("Building context...")
    # In a real impl, this would call UserService/ContextPruner
    # For now, we assume context is passed in state.context_data or we mock it
    # We can inject services into the state if needed, or use a global service locator
    
    # Placeholder: Retrieve context
    user_id = state.context_data.get("user_id")
    # ... logic to fetch user profile ...
    
    state.context_data["user_context"] = {"name": "User", "preferences": {}}
    return state

async def retrieval_node(state: WorkflowState) -> WorkflowState:
    """RAG Retrieval."""
    query = state.messages[-1]["content"] if state.messages else ""
    # In real impl: GalaxyService.hybrid_search(query)
    
    # Placeholder
    state.context_data["knowledge"] = "" 
    return state

async def generation_node(state: WorkflowState) -> WorkflowState:
    """LLM Generation (Streaming)."""
    # We need to access the 'stream_callback' from context to yield tokens
    stream_callback = state.context_data.get("stream_callback")
    
    # Cast to Dict to satisfy type checker
    user_context = state.context_data.get("user_context", {})
    if not isinstance(user_context, dict):
        user_context = {}

    system_prompt = build_system_prompt(
        user_context,
        conversation_history={"messages": state.messages[:-1]} # Naive history
    )
    
    user_message = state.messages[-1]["content"] or ""
    tools = state.context_data.get("tools_schema", [])
    
    full_response = ""
    tool_calls = []
    
    # We assume llm_service is available globally
    async for chunk in llm_service.chat_stream_with_tools(
        system_prompt=system_prompt,
        user_message=user_message,
        tools=tools
    ):
        if chunk.type == "text":
            full_response += chunk.content
            if stream_callback:
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=chunk.content
                ))
        elif chunk.type == "tool_call_end":
            tool_calls.append(chunk)
            if stream_callback:
                await stream_callback(agent_service_pb2.ChatResponse(
                    tool_call=agent_service_pb2.ToolCall(
                        id=chunk.tool_call_id,
                        name=chunk.tool_name,
                        arguments=json.dumps(chunk.full_arguments)
                    )
                ))
        elif chunk.type == "usage":
            if stream_callback:
                await stream_callback(agent_service_pb2.ChatResponse(
                    usage=agent_service_pb2.Usage(
                        prompt_tokens=chunk.prompt_tokens or 0,
                        completion_tokens=chunk.completion_tokens or 0,
                        total_tokens=(chunk.prompt_tokens or 0) + (chunk.completion_tokens or 0)
                    )
                ))

    state.append_message("assistant", full_response)
    if tool_calls:
        state.context_data["tool_calls"] = tool_calls
        state.next_step = "tool_execution"
    else:
        state.next_step = "__end__"
        
    return state

async def tool_execution_node(state: WorkflowState) -> WorkflowState:
    """Execute Tools."""
    tool_calls = state.context_data.get("tool_calls", [])
    executor = ToolExecutor() # Should be injected or cached
    
    stream_callback = state.context_data.get("stream_callback")
    user_id = state.context_data.get("user_id", "")
    db_session = state.context_data.get("db_session")

    for tc in tool_calls:
        if stream_callback:
            await stream_callback(agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                    details=f"Executing {tc.tool_name}..."
                )
            ))
        
        # Parse arguments if needed (ToolExecutor expects dict)
        args = tc.full_arguments
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {}

        result = await executor.execute_tool_call(
            tool_name=tc.tool_name,
            arguments=args,
            user_id=user_id,
            db_session=db_session
        )
        
        # ToolResult object to JSON
        result_json = json.dumps({
            "success": result.success,
            "result": result.data,
            "error": result.error_message
        })
        state.append_message("tool", result_json, name=tc.tool_name)
        
    # Clear tool calls and loop back to generation
    state.context_data["tool_calls"] = []
    # If we want to feed result back to LLM:
    state.next_step = "generation" 
    
    return state


# ==========================================
# Graph Definition
# ==========================================

def create_standard_chat_graph() -> StateGraph:
    graph = StateGraph("StandardChat")
    
    graph.add_node("context_builder", context_builder_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("generation", generation_node)
    graph.add_node("tool_execution", tool_execution_node)
    
    graph.set_entry_point("context_builder")
    
    graph.add_edge("context_builder", "retrieval")
    graph.add_edge("retrieval", "generation")
    
    # Conditional edge from generation
    def generation_router(state: WorkflowState) -> str:
        return state.next_step or "__end__"
        
    graph.add_conditional_edge("generation", generation_router)
    
    # Tool execution loops back to generation (to interpret results)
    graph.add_edge("tool_execution", "generation")
    
    return graph
