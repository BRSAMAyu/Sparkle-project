from typing import Literal, Optional
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from loguru import logger

from app.agents.graph.state import SparkleState
from app.agents.graph.llm_factory import LLMFactory

# 1. 定义路由输出结构
class RouteDecision(BaseModel):
    """路由决策结构"""
    target_agent: Literal["galaxy_guide", "time_tutor", "study_buddy", "exam_oracle", "human_assist"] = Field(
        ...,
        description="The specialist agent best suited to handle the user query."
    )
    reasoning: str = Field(..., description="Brief reason for this routing decision.")
    needs_clarification: bool = Field(False, description="True if user query is too vague.")

# Planning status constants
PLANNING_STATUSES = ("gathering_info", "drafting", "reviewing", "executing", "completed")

def _infer_plan_type(state: SparkleState) -> str:
    """Infer plan type from context and messages."""
    messages = state.get("messages", [])
    if not messages:
        return "routine"

    # Get user message for context
    last_message = messages[-1]
    user_query = last_message.content.lower() if last_message else ""

    # Infer plan type from keywords
    if any(k in user_query for k in ["sprint", "突击", "冲刺", "cram", "focus"]):
        return "sprint"
    elif any(k in user_query for k in ["week", "weekly", "周计划", "本周"]):
        return "routine"
    elif any(k in user_query for k in ["month", "monthly", "月计划", "长期"]):
        return "long_term"

    return "routine"

# 2. 路由节点函数
async def router_node(state: SparkleState):
    """
    语义路由节点
    分析用户意图，分发给专业 Agent

    P0 Fix #3: Now sets planning_status and current_plan context.
    """
    # 获取最后一条消息
    last_message = state["messages"][-1]
    user_query = last_message.content

    # Get current planning status
    current_status = state.get("planning_status")

    # Set initial planning status if not set or completed
    if current_status in [None, "completed"]:
        planning_status = "gathering_info"
    elif current_status in PLANNING_STATUSES:
        planning_status = current_status
    else:
        planning_status = "gathering_info"

    # 获取轻量级模型
    llm = LLMFactory.get_llm("router")

    # 绑定结构化输出 (Function Calling / JSON Mode)
    structured_llm = llm.with_structured_output(RouteDecision)

    # 提示词
    system_prompt = """You are the Dispatcher for Sparkle AI.
    Analyze the user's query and route it to the best specialist:

    - galaxy_guide: Knowledge graph, concepts, prerequisites, 'what is X', learning paths.
    - time_tutor: Scheduling, tasks, planning, deadlines, tomato timer.
    - study_buddy: General chat, emotional support, simple Q&A, study motivation.
    - exam_oracle: Exam predictions, mock tests, past paper analysis.
    - human_assist: User explicitly asks for human help or system cannot handle.

    If query is ambiguous, default to 'study_buddy'.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{query}")
    ])

    # 执行推理
    decision: RouteDecision = await structured_llm.ainvoke({"query": user_query})

    # Build state updates
    state_updates = {
        "next_step": decision.target_agent,
        "active_agent": "router",
        "planning_status": planning_status,
    }

    # Update current_plan if we have an executable plan with plan_id
    executable_plan = state.get("executable_plan")
    if executable_plan and isinstance(executable_plan, dict):
        plan_id = executable_plan.get("plan_id")
        if plan_id:
            current_plan = state.get("current_plan", {})
            # Update existing or create new
            if not current_plan or not isinstance(current_plan, dict):
                current_plan = {}
            state_updates["current_plan"] = {
                "plan_id": plan_id,
                "plan_type": _infer_plan_type(state),
                "status": "drafting",
            }
            # Transition planning_status to drafting
            state_updates["planning_status"] = "drafting"
            logger.info(f"Router: Set current_plan to {plan_id}, status=drafting")

    return state_updates
