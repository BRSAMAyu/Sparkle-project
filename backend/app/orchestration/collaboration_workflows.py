import json
from typing import Dict, Any, List
from loguru import logger
from app.orchestration.statechart_engine import StateGraph, WorkflowState
from app.services.llm_service import llm_service

# ==========================================
# 1. Node Implementations
# ==========================================

async def planner_node(state: WorkflowState) -> WorkflowState:
    """
    Agent responsible for breaking down complex tasks.
    """
    logger.info("🧠 [Planner] Analyzing request...")
    
    # Extract user request
    last_msg = state.messages[-1]["content"] if state.messages else ""
    
    # Simulate LLM call for planning (using actual service in prod)
    # prompt = f"Analyze this request and break it down: {last_msg}"
    # response = await llm_service.get_completion(prompt)
    
    # For now, we simulate a plan
    plan = {
        "steps": [
            {"id": 1, "action": "search", "query": last_msg},
            {"id": 2, "action": "synthesize", "focus": "key insights"}
        ]
    }
    
    state.context_data["plan"] = plan
    state.append_message("assistant", f"I have created a plan with {len(plan['steps'])} steps.", name="Planner")
    
    return state

async def executor_node(state: WorkflowState) -> WorkflowState:
    """
    Agent responsible for executing steps.
    """
    logger.info("⚙️ [Executor] Executing plan...")
    
    plan = state.context_data.get("plan", {})
    steps = plan.get("steps", [])
    
    results = []
    for step in steps:
        # Simulate execution
        results.append(f"Executed step {step['id']}: {step['action']}")
    
    state.context_data["execution_results"] = results
    state.append_message("assistant", f"Executed {len(results)} steps.", name="Executor")
    
    return state

async def reviewer_node(state: WorkflowState) -> WorkflowState:
    """
    Agent responsible for quality assurance.
    """
    logger.info("🔍 [Reviewer] Checking results...")
    
    results = state.context_data.get("execution_results", [])
    
    # Simulate review logic
    if not results:
        state.errors.append("No results to review")
    else:
        state.context_data["review_status"] = "approved"
        state.append_message("assistant", "Plan execution approved.", name="Reviewer")
        
    return state

# ==========================================
# 2. Routing Logic
# ==========================================

def review_router(state: WorkflowState) -> str:
    """
    Decide if we need to loop back to planner or finish.
    """
    if state.errors:
        return "planner" # Loop back on error
    return "__end__"

# ==========================================
# 3. Workflow Factory
# ==========================================

def create_collaboration_workflow() -> StateGraph:
    """
    Creates the 'Task Decomposition & Execution' workflow.
    Planner -> Executor -> Reviewer -> (End or Loop)
    """
    workflow = StateGraph("CollaborativeTaskSolving")
    
    # Register Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("reviewer", reviewer_node)
    
    # Set Entry Point
    workflow.set_entry_point("planner")
    
    # Define Edges
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "reviewer")
    
    # Conditional Edge from Reviewer
    workflow.add_conditional_edge("reviewer", review_router)
    
    return workflow
