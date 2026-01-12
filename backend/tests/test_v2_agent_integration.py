import asyncio
import json
import sys
import os
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.language_models import FakeListChatModel

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v2.agent_graph import router as agent_router

# --- 1. Setup Mock App ---
app = FastAPI()
app.include_router(agent_router, prefix="/api/v2/agent")
client = TestClient(app)

# --- 2. Mock LLM Responses ---
# We need to simulate the LLM's behavior for the Router and the Agent.

# Mock Router Response (Function Calling / Structured Output)
# Since we are using with_structured_output, the mock needs to handle that.
# However, FakeListChatModel doesn't support with_structured_output natively in a simple way 
# without some setup.
# 
# A simpler approach is to mock the `LLMFactory.get_llm` to return a MagicMock
# that has an `ainvoke` method returning what we want.

def mock_get_llm(agent_role, override_model=None):
    """
    Return a mock LLM based on the role.
    """
    mock_llm = MagicMock()
    
    # Setup async invoke mock
    async def async_response(*args, **kwargs):
        return AIMessage(content="Mocked response")

    # If it's the router, it needs to return a structured object (RouteDecision)
    if agent_role == "router":
        from app.agents.graph.nodes.router import RouteDecision
        
        # Mocking the `with_structured_output` chain
        mock_structured_llm = MagicMock()
        
        async def mock_router_invoke(*args, **kwargs):
            # Simulate routing to GalaxyGuide
            return RouteDecision(
                target_agent="galaxy_guide",
                reasoning="User asked about calculus, which fits GalaxyGuide.",
                needs_clarification=False
            )
        
        mock_structured_llm.ainvoke.side_effect = mock_router_invoke
        mock_llm.with_structured_output.return_value = mock_structured_llm
        
    elif agent_role == "galaxy_guide":
        # Galaxy Guide returns a message, potentially with tool calls or just text
        async def mock_galaxy_invoke(messages):
            # Simulate a response
            return AIMessage(content="[GalaxyGuide] Based on the Knowledge Graph, Calculus requires Algebra.")
        
        # Handle bind_tools
        mock_bound_llm = MagicMock()
        mock_bound_llm.ainvoke.side_effect = mock_galaxy_invoke
        mock_llm.bind_tools.return_value = mock_bound_llm

    else:
        # Default mock
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke.side_effect = async_response

    return mock_llm

# --- 3. Run Test ---
@patch("app.agents.graph.nodes.router.LLMFactory.get_llm", side_effect=mock_get_llm)
@patch("app.agents.graph.nodes.galaxy_guide.LLMFactory.get_llm", side_effect=mock_get_llm)
@patch("app.agents.graph.nodes.exam_oracle.LLMFactory.get_llm", side_effect=mock_get_llm)
@patch("app.agents.graph.nodes.time_tutor.LLMFactory.get_llm", side_effect=mock_get_llm)
def test_v2_agent_flow(mock_get_llm_time, mock_get_llm_exam, mock_get_llm_galaxy, mock_get_llm_router):
    print("🚀 Starting V2 Agent Integration Test (Mocked)...")
    
    payload = {
        "message": "我想学习微积分",
        "session_id": "test-session-v2-mock",
        "stream": True
    }
    
    # Use TestClient to send request
    # Note: StreamingResponse with TestClient needs careful handling or using the iterator.
    
    try:
        with client.stream("POST", "/api/v2/agent/chat", json=payload) as response:
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code}")
                print(response.read())
                return

            print("--- Stream Started ---")
            for line in response.iter_lines():
                if not line:
                    continue
                
                print(f"Received: {line}")
                
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        print("\n✅ Stream Completed")
                        break
                        
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_v2_agent_flow()