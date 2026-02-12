from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.llm_factory import LLMFactory
from app.agents.graph.nodes.registry_tools import create_knowledge_node, query_knowledge
from app.agents.graph.state import SparkleState


DEEP_ANALYST_PLANNING_PROMPT = (
    "You are in planning-only mode. Perform deep analysis planning with evidence retrieval. "
    "Use tool calls (query_knowledge, create_knowledge_node) when needed. "
    "Do not provide final narrative answers."
)


async def deep_analyst_node(state: SparkleState):
    messages = state["messages"]
    collaboration_context = state.get("collaboration_context")
    if collaboration_context:
        messages = list(messages)
        messages.append(HumanMessage(content=collaboration_context))

    if state.get("planning_mode") or state.get("_planning_mode"):
        messages = list(messages)
        messages.insert(0, SystemMessage(content=DEEP_ANALYST_PLANNING_PROMPT))

    llm = LLMFactory.get_llm("deep_analyst")
    llm_with_tools = llm.bind_tools([query_knowledge, create_knowledge_node])
    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "active_agent": "deep_analyst",
        "next_step": None,
    }

