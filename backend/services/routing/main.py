import sys
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Add backend to path to allow importing app modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.routing.router_node import RouterNode
from app.core.cache import cache_service
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache_service.init_redis()
    yield

app = FastAPI(title="Sparkle Routing Service", version="1.0.0", lifespan=lifespan)

class RouteRequest(BaseModel):
    messages: List[Dict[str, Any]]
    context_data: Dict[str, Any]
    routes: List[str]
    user_id: str

class RouteResponse(BaseModel):
    decision: str
    confidence: float
    reasoning: str


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "routing"}

@app.post("/route", response_model=RouteResponse)
async def route_request(req: RouteRequest):
    try:
        # Mocking WorkflowState to fit RouterNode interface
        # In a real microservice, we might extract the logic or share the data model
        class MockState:
            def __init__(self, messages, context):
                self.messages = messages
                self.context_data = context
        
        state = MockState(req.messages, req.context_data)
        
        # Initialize RouterNode
        router = RouterNode(
            routes=req.routes,
            redis_client=cache_service.redis,
            user_id=req.user_id
        )
        
        # RouterNode returns state with updated context_data['router_decision']
        # We need to adapt this.
        # Looking at router_node.py, it calls self.semantic_router.route or similar.
        # But RouterNode.__call__ does the full logic.
        
        result_state = await router(state)
        
        decision = result_state.context_data.get('router_decision', 'generation')
        confidence = result_state.context_data.get('router_confidence', 0.0)
        reasoning = result_state.context_data.get('router_reasoning', '')
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": reasoning
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
