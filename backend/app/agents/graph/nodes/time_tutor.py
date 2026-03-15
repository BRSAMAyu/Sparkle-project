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
from app.orchestration.agent_activity import emit_agent_activity, get_stream_callback

# --- 2. 节点逻辑 ---

async def time_tutor_node(state: SparkleState, config: dict | None = None):
    """
    Time Tutor 专家节点
    负责任务管理、日程规划
    """
    stream_cb = get_stream_callback(config)
    agent_id = "time_tutor"
    await emit_agent_activity(stream_cb, agent_id=agent_id, status="active")
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

    try:
        response = await llm_with_tools.ainvoke(messages)
        duration_ms = (time.time() - started_at) * 1000
        result_summary = None
        content = getattr(response, "content", None)
        if content:
            result_summary = str(content)[:80]
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="completed",
            duration_ms=duration_ms,
            result_summary=result_summary,
        )
    except Exception as exc:
        duration_ms = (time.time() - started_at) * 1000
        await emit_agent_activity(
            stream_cb,
            agent_id=agent_id,
            status="error",
            duration_ms=duration_ms,
            result_summary=str(exc)[:80],
        )
        raise

    return {
        "messages": [response],
        "active_agent": "time_tutor",
        "next_step": None
    }
