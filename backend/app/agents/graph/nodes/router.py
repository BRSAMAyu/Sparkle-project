from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.graph.expert_registry import get_graph_routable_targets, resolve_node_name
from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.state import SparkleState


# 1. 定义路由输出结构
class RouteDecision(BaseModel):
    """路由决策结构"""
    target_agent: str = Field(..., description="The specialist agent best suited to handle the user query.")
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

    routable_targets = get_graph_routable_targets()
    target_list_text = "\n    - " + "\n    - ".join(routable_targets)

    # 提示词
    system_prompt = """You are the Dispatcher for Sparkle AI.
    Analyze the user's query and route it to the best specialist.
    Allowed targets are:
    {target_list}

    If query is ambiguous, default to 'study_buddy'.

    Return JSON with keys: target_agent, reasoning, needs_clarification.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{query}")
    ])

    # 执行推理
    chain = prompt | structured_llm
    try:
        decision: RouteDecision = await chain.ainvoke({"query": user_query, "target_list": target_list_text})
    except Exception as exc:
        logger.warning(f"Router LLM failed, falling back to study_buddy: {exc}")
        decision = RouteDecision(
            target_agent="study_buddy",
            reasoning="Fallback routing due to LLM parse failure.",
            needs_clarification=False,
        )

    resolved_target = resolve_node_name(decision.target_agent) or "study_buddy"
    if resolved_target != decision.target_agent:
        decision = RouteDecision(
            target_agent=resolved_target,
            reasoning=f"{decision.reasoning} | normalized:{resolved_target}",
            needs_clarification=decision.needs_clarification,
        )

    # Build state updates
    state_updates = {
        "next_step": decision.target_agent,
        "active_agent": "router",
        "planning_status": planning_status,
    }

    # Determine collaboration mode once per request to avoid routing errors
    if not state.get("collaboration_mode"):
        try:
            from app.agents.graph.nodes.collaboration import _analyze_collaboration_needs
            collaboration_plan = _analyze_collaboration_needs(user_query)
            if collaboration_plan.get("mode") != "single":
                state_updates.update({
                    "collaboration_mode": collaboration_plan.get("mode"),
                    "collaboration_agents": collaboration_plan.get("agents", []),
                    "collaboration_order": collaboration_plan.get("order", []),
                    "collaboration_index": 0,
                    "next_step": "collaboration",
                })
            else:
                state_updates["collaboration_mode"] = "single"
        except Exception as exc:
            logger.warning(f"Failed to analyze collaboration needs: {exc}")

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
