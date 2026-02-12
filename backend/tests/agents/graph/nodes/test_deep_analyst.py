import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.graph.nodes.deep_analyst import deep_analyst_node


class _DummyLLM:
    def bind_tools(self, tools):
        self._tools = tools
        return self

    async def ainvoke(self, messages):
        return AIMessage(content="planned", tool_calls=[{"id": "c1", "name": "query_knowledge", "args": {"query": "x"}}])


@pytest.mark.asyncio
async def test_deep_analyst_node_returns_agent_response(monkeypatch):
    monkeypatch.setattr("app.agents.graph.nodes.deep_analyst.LLMFactory.get_llm", lambda _role: _DummyLLM())

    state = {
        "messages": [HumanMessage(content="分析微积分的本质")],
        "planning_mode": True,
    }

    result = await deep_analyst_node(state)

    assert result["active_agent"] == "deep_analyst"
    assert result["messages"]
    assert result["messages"][0].tool_calls
