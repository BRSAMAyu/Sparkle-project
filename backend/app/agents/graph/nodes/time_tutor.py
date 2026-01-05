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
