from typing import TypedDict, Annotated, List, Optional, Dict, Any, Union
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class SparkleState(TypedDict):
    """
    Sparkle 全局状态定义
    承载整个对话生命周期的数据
    """
    # ==========================
    # 1. 基础消息历史 (Append-only)
    # ==========================
    # 自动合并历史消息，支持 OpenAI 格式
    messages: Annotated[List[BaseMessage], operator.add]
    
    # ==========================
    # 2. 上下文信息 (Context)
    # ==========================
    user_id: str
    session_id: str
    user_profile: Optional[Dict[str, Any]] # 用户画像(年级, 强弱项)
    
    # ==========================
    # 3. 路由与控制 (Control)
    # ==========================
    # 下一步的计划/意图，由 Router 生成
    next_step: Optional[str] 
    
    # 当前激活的 Agent (用于 UI 展示)
    active_agent: Optional[str]
    
    # ==========================
    # 4. 人工介入 (Human-in-the-loop)
    # ==========================
    # 是否需要人工审批敏感操作
    require_approval: bool
    # 审批上下文 (如: "即将删除 5 个任务，是否确认？")
    approval_context: Optional[str]
    # 用户的审批结果 (Approved/Rejected)
    approval_result: Optional[str]

    # ==========================
    # 5. 错误处理 (Error Handling)
    # ==========================
    error: Optional[str]
