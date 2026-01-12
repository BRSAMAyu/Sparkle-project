from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from app.agents.graph.state import SparkleState
from app.agents.graph.nodes.router import router_node
from app.agents.graph.nodes.galaxy_guide import galaxy_guide_node, search_knowledge_graph, get_prerequisites
from app.agents.graph.nodes.exam_oracle import exam_oracle_node, analyze_past_papers, predict_exam_focus
from app.agents.graph.nodes.time_tutor import time_tutor_node, create_study_task, suggest_pomodoro_schedule

# --- 1. 条件边逻辑 (Conditional Edges) ---

def route_after_router(state: SparkleState):
    """Router 节点后的分支逻辑"""
    target = state.get("next_step")
    
    if target == "galaxy_guide":
        return "galaxy_guide"
    elif target == "exam_oracle":
        return "exam_oracle"
    elif target == "time_tutor":
        return "time_tutor"
    elif target == "study_buddy":
        return "study_buddy" # 暂未实现，可指向 TimeTutor 或 GalaxyGuide 兜底
    elif target == "human_assist":
        return "human_node"
    else:
        # 默认兜底：如果无法识别，交给 TimeTutor 做通用闲聊 (或实现专门的 GeneralChat)
        return "time_tutor"

def route_after_agent(state: SparkleState):
    """Agent 节点后的逻辑 (处理工具调用)"""
    last_message = state["messages"][-1]
    
    # 如果 Agent 想要调用工具
    if last_message.tool_calls:
        return "tools"
    
    # 否则任务结束
    return END

# --- 2. 构建图 (Graph Construction) ---

workflow = StateGraph(SparkleState)

# (A) 添加 Agent 节点
workflow.add_node("router", router_node)
workflow.add_node("galaxy_guide", galaxy_guide_node)
workflow.add_node("exam_oracle", exam_oracle_node)
workflow.add_node("time_tutor", time_tutor_node)

# (B) 添加工具节点 (所有 Agent 的工具汇聚于此，也可拆分为多个 ToolNode)
all_tools = [
    search_knowledge_graph, get_prerequisites,   # Galaxy
    analyze_past_papers, predict_exam_focus,     # Exam
    create_study_task, suggest_pomodoro_schedule # Time
]
tool_node = ToolNode(all_tools)
workflow.add_node("tools", tool_node)

# (C) 添加虚拟人工节点
def human_node(state: SparkleState):
    pass 
workflow.add_node("human_node", human_node)

# --- 3. 连接边 (Edges) ---

# 入口 -> Router
workflow.set_entry_point("router")

# Router -> Agents
workflow.add_conditional_edges(
    "router",
    route_after_router,
    {
        "galaxy_guide": "galaxy_guide",
        "exam_oracle": "exam_oracle",
        "time_tutor": "time_tutor",
        "study_buddy": "time_tutor", # 暂时 fallback
        "human_node": "human_node",
        END: END
    }
)

# Agents -> Tools OR End
for agent_name in ["galaxy_guide", "exam_oracle", "time_tutor"]:
    workflow.add_conditional_edges(
        agent_name,
        route_after_agent,
        {
            "tools": "tools",
            END: END
        }
    )

# Tools -> Back to Agent (需要知道是谁调用的工具)
# 简化策略：工具执行完，统一回到 Router 进行下一轮判断？
# 或者：LangGraph 的 ToolNode 默认行为是返回给 Caller。
# 这里我们需要显式指定返回路径。为简单起见，工具执行后我们统一检查是否任务完成。
# *更佳实践*: 每个 Agent 应该有自己的 SubGraph 或者明确的回边。
# 在此架构中，我们让工具执行完后，重新回到 Router 进行"下一轮意图识别"通常更灵活，
# 但为了保持上下文连贯，通常是回到调用者。

# 修正：为每个 Agent 建立回边是 LangGraph 的标准做法，但这需要条件边。
# 简便方案：让 Tools 节点执行完后，统一路由回 Router (让 Router 决定是否结束)。
workflow.add_edge("tools", "router") 

# --- 4. 编译 (Compile) ---

checkpointer = MemorySaver()

sparkle_graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_node"]
)