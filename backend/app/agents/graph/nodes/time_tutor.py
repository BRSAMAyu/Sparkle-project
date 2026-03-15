import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import (
    batch_create_tasks,
    create_plan,
    create_task,
    generate_tasks_for_plan,
    suggest_focus_session,
)
from app.agents.graph.state import SparkleState
from app.core.metrics import AGENT_PERFORMANCE_RECORDED_TOTAL
from app.orchestration.agent_activity import emit_agent_activity, get_stream_callback
from app.orchestration.agent_scoring import AgentScoringService

# --- prompt helpers ---
def _build_system_prompt(state: SparkleState, *, planning: bool) -> str:
    collaboration_mode = str(state.get("collaboration_mode") or "").strip()
    collaboration_agents = [
        str(agent).strip()
        for agent in (state.get("collaboration_agents") or [])
        if str(agent).strip()
    ]
    other_agents = [agent for agent in collaboration_agents if agent != "time_tutor"]

    if planning:
        prompt = (
            "你是时间教练（规划模式），擅长把目标拆成可执行的时间安排。\n"
            "## 思维框架\n"
            "先估算可用时间与节奏，再拆分任务与里程碑。\n"
            "## 规划输出\n"
            "必须用 tool calls 生成计划或任务，不要直接给最终答案。"
        )
    else:
        prompt = (
            "你是时间教练，擅长把目标转化为清晰的时间安排与执行节奏。\n"
            "## 思维框架\n"
            "先估算任务规模，再给出节奏与优先级建议。\n"
            "## 输出格式\n"
            "1. 核心判断（1 句）\n"
            "2. 2-3 条安排建议（含时间/节奏）\n"
            "3. 1 条可执行建议或下一步动作\n"
            "## 个性化适配\n"
            "若上文包含用户偏好或难度提示，请据此调整节奏与任务粒度。"
        )

    if collaboration_mode and other_agents:
        prompt += (
            "\n\n## 协作须知\n"
            f"协作模式：{collaboration_mode}\n"
            f"其他参与专家：{', '.join(other_agents)}\n"
            "专注于时间安排与执行节奏，不要重复他人内容。\n"
            "关键论点可简短标注“时间教练视角”。"
        )
    return prompt

# --- 2. 节点逻辑 ---

async def time_tutor_node(state: SparkleState, config: dict | None = None):
    """
    Time Tutor 专家节点
    负责任务管理、日程规划
    """
    stream_cb = get_stream_callback(config)
    agent_id = "time_tutor"
    activity_metadata = {
        "collaboration_mode": str(state.get("collaboration_mode") or ""),
        "phase": "analysis",
    }
    await emit_agent_activity(stream_cb, agent_id=agent_id, status="active", metadata=activity_metadata)
    started_at = time.time()
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

    planning_mode = state.get("planning_mode") or state.get("_planning_mode")
    messages = list(messages)
    messages.insert(0, SystemMessage(content=_build_system_prompt(state, planning=bool(planning_mode))))

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

    try:
        response = await llm_with_tools.ainvoke(messages)
        duration_ms = (time.time() - started_at) * 1000
        tool_calls_count = len(getattr(response, "tool_calls", []) or [])
        result_summary = None
        content = getattr(response, "content", None)
        if content:
            result_summary = str(content)[:80]
        await AgentScoringService(None).record_from_runtime(
            redis_client=(config or {}).get("configurable", {}).get("redis_client"),
            state=state,
            agent_id=agent_id,
            latency_ms=duration_ms,
            success=True,
            tool_calls_count=tool_calls_count,
            result_used=tool_calls_count > 0,
            intent_type=((state.get("_planning_constraints") or {}).get("route_intent")),
        )
        AGENT_PERFORMANCE_RECORDED_TOTAL.labels(agent_id=agent_id, success="true").inc()
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="completed",
            duration_ms=duration_ms,
            result_summary=result_summary,
            metadata=activity_metadata,
        )
    except Exception as exc:
        duration_ms = (time.time() - started_at) * 1000
        await AgentScoringService(None).record_from_runtime(
            redis_client=(config or {}).get("configurable", {}).get("redis_client"),
            state=state,
            agent_id=agent_id,
            latency_ms=duration_ms,
            success=False,
            tool_calls_count=0,
            result_used=False,
            intent_type=((state.get("_planning_constraints") or {}).get("route_intent")),
        )
        AGENT_PERFORMANCE_RECORDED_TOTAL.labels(agent_id=agent_id, success="false").inc()
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="error",
            duration_ms=duration_ms,
            result_summary=str(exc)[:80],
            metadata=activity_metadata,
        )
        raise

    return {
        "messages": [response],
        "active_agent": "time_tutor",
        "next_step": None
    }
