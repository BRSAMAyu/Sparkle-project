from typing import List
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from app.agents.graph.state import SparkleState
from app.agents.graph.llm_factory import LLMFactory

# --- 1. 定义工具 (Mock for now, will connect to real services) ---
@tool
def search_knowledge_graph(keyword: str):
    """Search for knowledge nodes in the Sparkle Galaxy."""
    # 实际项目中这里调用 GalaxyService
    return f"Found nodes related to '{keyword}': [Node A (ID: 1), Node B (ID: 2)]"

@tool
def get_prerequisites(node_id: str):
    """Get prerequisite knowledge points for a specific node."""
    return f"Prerequisites for Node {node_id}: [Basic Algebra, Calculus I]"

# --- 2. 节点逻辑 ---
async def galaxy_guide_node(state: SparkleState):
    """
    Knowledge Galaxy 专家
    负责解释概念、查询图谱
    """
    messages = state["messages"]
    
    # 获取 DeepSeek 或强推理模型
    llm = LLMFactory.get_llm("galaxy_guide")
    
    # 绑定工具
    tools = [search_knowledge_graph, get_prerequisites]
    llm_with_tools = llm.bind_tools(tools)
    
    # 执行
    # 注意：这里我们只传入 messages，LangGraph 会自动处理历史
    response = await llm_with_tools.ainvoke(messages)
    
    return {
        "messages": [response],
        "active_agent": "galaxy_guide",
        "next_step": None # 任务结束 (除非有 Tool Call，LangGraph 引擎会自动处理)
    }
