from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.graph.state import SparkleState
from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import (
    create_task,
    batch_create_tasks,
    create_plan,
    generate_tasks_for_plan,
    suggest_focus_session,
)

# --- 2. 节点逻辑 ---

async def time_tutor_node(state: SparkleState):
    """
    Time Tutor 专家节点
    负责任务管理、日程规划
    """
    messages = state["messages"]
    
    # 1. Handle Collaboration Context
    collaboration_context = state.get("collaboration_context")
    if collaboration_context:
        # Create a shallow copy to avoid modifying the global list in place if not intended
        # (Though usually state update appends, here we are preparing prompt)
        messages = list(messages)
        messages.append(HumanMessage(content=f"[System] Collaboration Context: {collaboration_context}"))

    # 2. Handle Review Feedback (Vision Item 8)
    review_feedback = state.get("review_feedback")
    if review_feedback:
        messages = list(messages) if not collaboration_context else messages
        decision = review_feedback.get("decision", "modify")
        comments = review_feedback.get("comments", "No comments")
        feedback_prompt = (
            f"[System] ALERT: The user has {decision} the previous plan.\n"
            f"Feedback: {comments}\n"
            f"Instruction: You MUST revise the plan/tasks to address this feedback explicitly."
        )
        messages.append(HumanMessage(content=feedback_prompt))

    if state.get("planning_mode") or state.get("_planning_mode"):
        messages = list(messages)
        messages.insert(
            0,
            SystemMessage(
                content=(
                    "You are in planning-only mode. Use tool calls to create plans and tasks "
                    "(create_plan, generate_tasks_for_plan, create_task, batch_create_tasks, "
                    "suggest_focus_session). Do not provide a final narrative response."
                )
            ),
        )
    
    # 使用高性价比模型 (GPT-4o-mini)
    llm = LLMFactory.get_llm("time_tutor")
    
    tools = [
        create_plan,
        generate_tasks_for_plan,
        create_task,
        batch_create_tasks,
        suggest_focus_session,
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    response = await llm_with_tools.ainvoke(messages)
    
    return {
        "messages": [response],
        "active_agent": "time_tutor",
        "next_step": None
    }
