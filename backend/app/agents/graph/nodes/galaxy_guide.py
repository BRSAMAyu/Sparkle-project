from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.state import SparkleState
from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import (
    query_knowledge,
    create_knowledge_node,
    link_nodes,
)

# --- 2. 节点逻辑 ---
async def galaxy_guide_node(state: SparkleState):
    """
    Knowledge Galaxy 专家
    负责解释概念、查询图谱
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
                    "You are in planning-only mode. Use tool calls to create a plan or retrieve "
                    "knowledge. Respond with one or more tool calls, not a final narrative answer."
                )
            ),
        )
    
    # 获取 DeepSeek 或强推理模型
    llm = LLMFactory.get_llm("galaxy_guide")
    
    # 绑定工具
    tools = [query_knowledge, create_knowledge_node, link_nodes]
    llm_with_tools = llm.bind_tools(tools)
    
    # 执行
    # 注意：这里我们只传入 messages，LangGraph 会自动处理历史
    response = await llm_with_tools.ainvoke(messages)
    
    return {
        "messages": [response],
        "active_agent": "galaxy_guide",
        "next_step": None # 任务结束 (除非有 Tool Call，LangGraph 引擎会自动处理)
    }
