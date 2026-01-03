from typing import List, Dict, Any
import asyncio
from loguru import logger

from app.orchestration.statechart_engine import StateGraph, WorkflowState
from app.agents.enhanced_agents import StudyPlannerAgent, ProblemSolverAgent
from app.agents.specialist_agents import MathAgent, CodeAgent, WritingAgent
from app.agents.base_agent import AgentContext

# ==========================================
# Graph-based Task Decomposition Workflow
# ==========================================

def _create_context(state: WorkflowState, query: str) -> AgentContext:
    return AgentContext(
        user_id=state.context_data.get("user_id", "unknown"),
        session_id=state.context_data.get("session_id", "unknown"),
        user_query=query,
        conversation_history=state.messages
    )

async def planner_node(state: WorkflowState) -> WorkflowState:
    logger.info("🤖 Planner: Analyzing request...")
    planner = StudyPlannerAgent()
    
    # Adapt WorkflowState to AgentContext
    query = state.messages[-1]["content"]
    context = _create_context(state, query)
    
    response = await planner.process(context)
    
    state.context_data["plan"] = response
    state.append_message("planner", response.response_text)
    
    # Determine required specialists
    # (Simplified logic from original workflow)
    needed = []
    if "math" in state.messages[-1]["content"].lower():
        needed.append("math_agent")
    if "code" in state.messages[-1]["content"].lower():
        needed.append("code_agent")
        
    state.context_data["needed_agents"] = needed
    return state

async def math_node(state: WorkflowState) -> WorkflowState:
    logger.info("🧮 Math Agent: Processing...")
    agent = MathAgent()
    context = _create_context(state, "Generate math exercises based on plan")
    response = await agent.process(context)
    state.append_message("math_agent", response.response_text)
    return state

async def code_node(state: WorkflowState) -> WorkflowState:
    logger.info("💻 Code Agent: Processing...")
    agent = CodeAgent()
    context = _create_context(state, "Generate code project based on plan")
    response = await agent.process(context)
    state.append_message("code_agent", response.response_text)
    return state

async def synthesizer_node(state: WorkflowState) -> WorkflowState:
    logger.info("📝 Synthesizer: Combining results...")
    # Combine all messages
    summary = "## Collaboration Result\n\n"
    for msg in state.messages:
        if msg["role"] not in ["user", "system"]:
            summary += f"### {msg['role']}\n{msg['content']}\n\n"
            
    state.append_message("assistant", summary)
    return state

def create_task_decomposition_graph() -> StateGraph:
    graph = StateGraph("TaskDecomposition")
    
    graph.add_node("planner", planner_node)
    graph.add_node("math_agent", math_node)
    graph.add_node("code_agent", code_node)
    graph.add_node("synthesizer", synthesizer_node)
    
    graph.set_entry_point("planner")
    
    # Dynamic Router for Parallel Execution
    # Since StateGraph engine supports parallel execution if next_step is a list
    # But currently add_conditional_edge expects a string return.
    # We will use a router that returns a list of nodes to execute in parallel?
    # My engine implementation:
    # if isinstance(node_action, list): ... this is for parallel *node* definition.
    # The transition logic:
    # if callable(edge): next_node = edge(state)
    # The loop: current_node_name = next_node.
    
    # To support dynamic parallel fan-out, the engine needs to handle list of next nodes.
    # Currently my engine's `invoke` loop handles one `current_node_name`.
    # It does NOT support dynamic parallel branching (Fork) in the transition logic yet.
    
    # Workaround: A "Dispatcher" node that calls the agents in parallel using asyncio.gather
    # inside the node itself, effectively embedding the parallel logic.
    
    async def dispatcher_node(state: WorkflowState) -> WorkflowState:
        needed = state.context_data.get("needed_agents", [])
        tasks = []
        if "math_agent" in needed:
            tasks.append(math_node(state.clone())) # Use clone for safety
        if "code_agent" in needed:
            tasks.append(code_node(state.clone()))
            
        if tasks:
            results = await asyncio.gather(*tasks)
            # Merge results
            for res in results:
                # Merge messages
                new_msgs = res.messages[len(state.messages):]
                state.messages.extend(new_msgs)
        
        return state

    graph.add_node("dispatcher", dispatcher_node)
    
    graph.add_edge("planner", "dispatcher")
    graph.add_edge("dispatcher", "synthesizer")
    graph.add_edge("synthesizer", "__end__")
    
    return graph
