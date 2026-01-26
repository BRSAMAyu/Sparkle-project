from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.state import SparkleState
from app.agents.graph.llm_factory import LLMFactory

from app.agents.graph.nodes.registry_tools import (
    query_knowledge,
    create_plan,
    generate_tasks_for_plan,
    create_task,
)

# --- 2. 节点逻辑 (Node Logic) ---

async def exam_oracle_node(state: SparkleState):
    """
    Exam Oracle 专家节点
    负责考点预测、真题分析、模拟出题、文档清洗、任务调度
    """
    messages = state["messages"]
    collaboration_context = state.get("collaboration_context")
    if collaboration_context:
        messages = list(messages)
        messages.append(HumanMessage(content=collaboration_context))

    if state.get("planning_mode") or state.get("_planning_mode"):
        messages = list(messages)
        messages.insert(
            0,
            SystemMessage(
                content=(
                    "You are in planning-only mode. Use tool calls to create exam-focused plans "
                    "and tasks (create_plan, generate_tasks_for_plan, create_task, query_knowledge). "
                    "Do not provide a final narrative response."
                )
            ),
        )
    
    # 使用强推理模型 (GPT-4o) 处理复杂分析
    llm = LLMFactory.get_llm("exam_oracle")
    
    # 绑定工具 (aligned with dynamic tool registry)
    tools = [
        query_knowledge,
        create_plan,
        generate_tasks_for_plan,
        create_task,
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    # 执行推理
    response = await llm_with_tools.ainvoke(messages)
    
    return {
        "messages": [response],
        "active_agent": "exam_oracle",
        "next_step": None 
    }
