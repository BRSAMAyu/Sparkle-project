from typing import Literal, Optional
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

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

# 2. 路由节点函数
async def router_node(state: SparkleState):
    """
    语义路由节点
    分析用户意图，分发给专业 Agent
    """
    # 获取最后一条消息
    last_message = state["messages"][-1]
    user_query = last_message.content
    
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
    
    # 更新状态
    return {
        "next_step": decision.target_agent,
        "active_agent": "router" # 瞬时状态
    }
