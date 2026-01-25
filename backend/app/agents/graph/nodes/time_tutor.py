from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from app.agents.graph.state import SparkleState
from app.agents.graph.llm_factory import LLMFactory

# --- 1. 定义工具 ---

@tool
def create_study_task(title: str, duration_minutes: int, priority: str = "medium"):
    """Create a new study task in the user's schedule."""
    # 实际对接 TaskService
    return f"Task created: '{title}' ({duration_minutes} min) - Priority: {priority}"

@tool
def suggest_pomodoro_schedule(available_minutes: int):
    """Generate a Pomodoro schedule based on available time."""
    cycles = available_minutes // 30
    return f"Suggested: {cycles} cycles of (25m Focus + 5m Break). Total: {cycles * 30} mins."

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
    
    # 使用高性价比模型 (GPT-4o-mini)
    llm = LLMFactory.get_llm("time_tutor")
    
    tools = [create_study_task, suggest_pomodoro_schedule]
    llm_with_tools = llm.bind_tools(tools)
    
    response = await llm_with_tools.ainvoke(messages)
    
    return {
        "messages": [response],
        "active_agent": "time_tutor",
        "next_step": None
    }
