from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from loguru import logger

from app.agents.graph.expert_registry import (
    get_graph_expert_specs,
    resolve_node_name,
)
from app.agents.graph.nodes.custom_expert import custom_expert_node
# Phase 3: Import collaboration nodes
from app.agents.graph.nodes.collaboration import (
    collaboration_aggregator_node,
    collaboration_node,
)
from app.agents.graph.nodes.registry_tools import (
    batch_create_tasks,
    create_knowledge_node,
    create_plan,
    create_task,
    generate_tasks_for_plan,
    link_nodes,
    query_error_history,
    query_knowledge,
    record_error,
    suggest_focus_session,
)
from app.agents.graph.nodes.router import router_node
from app.agents.graph.state import SparkleState


EXPERT_SPECS = get_graph_expert_specs()
EXPERT_NODE_NAMES = [spec.node_name for spec in EXPERT_SPECS]
RUNTIME_NODE_NAMES = [*EXPERT_NODE_NAMES, "custom_expert"]

# --- 1. 条件边逻辑 (Conditional Edges) ---

def route_after_router(state: SparkleState):
    """Router 节点后的分支逻辑"""
    target = state.get("next_step")
    if target == "human_assist":
        return "human_node"
    resolved = resolve_node_name(target)
    if resolved:
        return resolved
    return "study_buddy"

def route_after_agent(state: SparkleState):
    """Agent 节点后的逻辑 (处理工具调用)"""
    last_message = state["messages"][-1]

    # 如果 Agent 想要调用工具
    if last_message.tool_calls:
        return "tools"

    # 否则任务结束
    return END

def route_after_agent_planning(state: SparkleState):
    """Agent 节点后的逻辑 (规划模式 - 不执行工具)

    Phase 2: 在规划模式下，当 Agent 生成 tool_calls 时，
    我们停止执行并返回计划，不实际执行工具。
    """
    last_message = state["messages"][-1]

    # 如果 Agent 想要调用工具，在规划模式下我们直接结束
    # tool_calls 会被提取到 ExecutablePlan 中
    if last_message.tool_calls:
        return END

    # 否则任务结束
    return END

# --- 2. 构建标准图 (Graph Construction) ---

workflow = StateGraph(SparkleState)

# (A) 添加 Agent 节点
workflow.add_node("router", router_node)
for spec in EXPERT_SPECS:
    workflow.add_node(spec.node_name, spec.node_handler)
workflow.add_node("custom_expert", custom_expert_node)

# (B) 添加工具节点 (所有 Agent 的工具汇聚于此，也可拆分为多个 ToolNode)
all_tools = [
    query_knowledge,
    create_knowledge_node,
    link_nodes,
    create_plan,
    generate_tasks_for_plan,
    create_task,
    batch_create_tasks,
    suggest_focus_session,
    record_error,
    query_error_history,
]
tool_node = ToolNode(all_tools)
workflow.add_node("tools", tool_node)

# (C) Human-in-the-loop node
# When the graph routes here with interrupt_before, execution pauses.
# The caller (orchestrator) inspects approval_context, presents it to the
# user, and resumes with approval_result set to "approved" or "rejected".
def human_node(state: SparkleState):
    result = state.get("approval_result")
    context = state.get("approval_context", "")
    if result == "approved":
        logger.info(f"Human approved: {context}")
        return {"approval_result": None, "require_approval": False}
    else:
        logger.info(f"Human rejected: {context}")
        return {"approval_result": None, "require_approval": False}
workflow.add_node("human_node", human_node)

# --- 3. 连接边 (Edges) ---

# 入口 -> Router
workflow.set_entry_point("router")

# Router -> Agents
router_edge_map = {name: name for name in RUNTIME_NODE_NAMES}
router_edge_map["human_node"] = "human_node"
router_edge_map[END] = END
workflow.add_conditional_edges("router", route_after_router, router_edge_map)

# Agents -> Tools OR End
for agent_name in RUNTIME_NODE_NAMES:
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

# Human node -> back to Router for next-step decision after approval
workflow.add_edge("human_node", "router")

# --- 4. 编译标准图 (Compile) ---

checkpointer = MemorySaver()

sparkle_graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_node"]
)


# ==========================================
# Phase 2: Planning-Only Graph (No Tool Execution)
# ==========================================

def create_planning_graph():
    """Create a planning-only graph that does NOT execute tools (Phase 3: with collaboration support).

    This graph is used by LangGraphPlanner to generate ExecutablePlan.
    It will route through agents but stop when tool_calls are generated,
    without actually executing them.

    Phase 3: Now supports multi-agent collaboration nodes.
    This ensures "planning without execution" constraint.
    """
    planning_workflow = StateGraph(SparkleState)

    # Add the same agent nodes (they do the planning/reasoning)
    planning_workflow.add_node("router", router_node)
    # Phase 3: Add collaboration node
    planning_workflow.add_node("collaboration", collaboration_node)
    for spec in EXPERT_SPECS:
        planning_workflow.add_node(spec.node_name, spec.node_handler)
    planning_workflow.add_node("custom_expert", custom_expert_node)
    # Phase 3: Add aggregator node
    planning_workflow.add_node("aggregator", collaboration_aggregator_node)
    # P0 Fix: Add reset_collaboration node for review feedback loop
    planning_workflow.add_node("reset_collaboration", reset_collaboration_node)

    # NO ToolNode in planning graph!
    # We stop at tool_calls generation

    # Entry point
    planning_workflow.set_entry_point("router")

    # Router -> Reset, Collaboration or Direct Agent (Phase 3 routing)
    router_planning_edges = {
        "reset_collaboration": "reset_collaboration",
        "collaboration": "collaboration",
        END: END,
    }
    for name in RUNTIME_NODE_NAMES:
        router_planning_edges[name] = name
    planning_workflow.add_conditional_edges("router", route_after_router_with_collaboration, router_planning_edges)

    # Reset -> Collaboration (after clearing review_feedback)
    planning_workflow.add_conditional_edges(
        "reset_collaboration",
        route_after_reset,
        {
            "collaboration": "collaboration"
        }
    )

    # Collaboration -> Agents (sequential execution)
    collaboration_edges = {"aggregator": "aggregator"}
    for name in RUNTIME_NODE_NAMES:
        collaboration_edges[name] = name
    planning_workflow.add_conditional_edges("collaboration", route_after_collaboration, collaboration_edges)

    # Agents -> Back to Collaboration or Aggregator
    for agent_name in RUNTIME_NODE_NAMES:
        planning_workflow.add_conditional_edges(
            agent_name,
            route_after_agent_in_collaboration,
            {
                "continue_collaboration": "collaboration",
                "aggregator": "aggregator",
                END: END
            }
        )

    # Aggregator -> End
    planning_workflow.add_edge("aggregator", END)

    # Compile with checkpointer
    planning_checkpointer = MemorySaver()

    return planning_workflow.compile(
        checkpointer=planning_checkpointer
    )


# ============ Phase 3: Collaboration Routing Functions ============

def reset_collaboration_node(state: SparkleState):
    """
    Reset collaboration state for replanning after review feedback.

    This node is called when review_feedback indicates modify/reject.
    It clears the feedback and resets collaboration index to trigger replanning.
    """
    return {
        "collaboration_index": 0,
        "review_feedback": None,  # Clear after processing to prevent infinite loop
    }

def route_after_reset(state: SparkleState) -> str:
    """After reset, always route back to collaboration for replanning."""
    return "collaboration"

def route_after_router_with_collaboration(state: SparkleState):
    """Router 后的路由（支持协作模式） (Phase 3)"""
    target = state.get("next_step")
    collaboration_mode = state.get("collaboration_mode")
    review_feedback = state.get("review_feedback")

    # Vision Item 8: Review Loop
    # If there is review feedback (Modify/Reject), route to reset node first
    # State mutation must happen in a node, not in a routing function
    if review_feedback and review_feedback.get("decision") in ["modify", "reject"]:
        return "reset_collaboration"

    # If collaboration_mode not set yet, route to collaboration node
    # to compute the plan and set state updates.
    if not collaboration_mode:
        return "collaboration"

    if collaboration_mode and collaboration_mode != "single":
        return "collaboration"
    resolved = resolve_node_name(target)
    if resolved:
        return resolved
    return "study_buddy"


def route_after_collaboration(state: SparkleState):
    """协作节点后的路由 (Phase 3)"""
    # Collaboration node sets next_step explicitly
    next_step = state.get("next_step")
    if next_step:
        resolved = resolve_node_name(next_step)
        if resolved:
            return resolved
    return "aggregator"


def route_after_agent_in_collaboration(state: SparkleState):
    """Agent 执行后的路由（协作模式） (Phase 3)"""
    collaboration_mode = state.get("collaboration_mode", "single")
    collaboration_order = state.get("collaboration_order", [])
    collaboration_index = state.get("collaboration_index", 0)

    if collaboration_mode != "single" and len(collaboration_order) > 1:
        # Check if more agents need to execute
        if collaboration_index < len(collaboration_order):
            return "continue_collaboration"

    return "aggregator"


# Singleton instance for planning graph
_planning_graph = None


def get_planning_graph():
    """Get the planning-only graph instance (singleton) (Phase 3: with collaboration support)."""
    global _planning_graph
    if _planning_graph is None:
        _planning_graph = create_planning_graph()
        logger.info("Planning-only graph created (Phase 3: with collaboration support)")
    return _planning_graph


# Export for use in LangGraphPlanner
sparkle_planning_graph = get_planning_graph()
