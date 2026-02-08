from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import query_error_history, record_error
from app.agents.graph.state import SparkleState


ERROR_ANALYST_PLANNING_PROMPT = (
    "You are in planning-only mode for error diagnosis. "
    "Classify error type, identify root cause, and use tool calls "
    "(query_error_history, record_error) as needed. "
    "Do not provide final narrative answers."
)


async def error_analyst_node(state: SparkleState):
    messages = state["messages"]
    collaboration_context = state.get("collaboration_context")
    if collaboration_context:
        messages = list(messages)
        messages.append(HumanMessage(content=collaboration_context))

    if state.get("planning_mode") or state.get("_planning_mode"):
        messages = list(messages)
        messages.insert(0, SystemMessage(content=ERROR_ANALYST_PLANNING_PROMPT))

    llm = LLMFactory.get_llm("error_analyst")
    llm_with_tools = llm.bind_tools([record_error, query_error_history])
    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "active_agent": "error_analyst",
        "next_step": None,
    }

