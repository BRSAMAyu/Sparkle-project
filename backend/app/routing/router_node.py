from typing import List, Dict, Any, Optional
from loguru import logger
import random

from app.orchestration.statechart_engine import WorkflowState
from app.routing.graph_router import GraphBasedRouter
from app.learning.bayesian_learner import BayesianLearner

class RouterNode:
    """
    Intelligent Router Node.
    Decides the next step in the workflow based on state and history.
    
    Integrates Graph-based routing (Phase 2) and Bayesian Learning (Phase 4).
    """
    def __init__(self, routes: List[str]):
        self.routes = routes
        self.graph_router = GraphBasedRouter()
        self.learner = BayesianLearner()

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        """
        Execute routing logic.
        Updates state.context_data['next_step']
        """
        # 1. Analyze intent (Placeholder for semantic analysis)
        last_msg = state.messages[-1]['content'] if state.messages else ""
        current_node = state.context_data.get("current_node", "orchestrator")
        
        # 2. Graph-based Routing (Phase 2)
        target_capability = self._extract_capability(last_msg)
        next_route = self.graph_router.find_route(current_node, target_capability)
        
        # 3. Adaptive Adjustment (Phase 4)
        if next_route:
            # Check success probability
            prob = self.learner.get_probability(current_node, next_route)
            if prob < 0.3:
                logger.warning(f"Low probability route {current_node}->{next_route} ({prob:.2f}), considering fallback")
                # Fallback logic here if needed
        else:
            # Fallback to simple routing if graph doesn't find path
            next_route = self._simple_route(last_msg)

        # 4. Learning Update (Mock - in real flow, this happens after execution)
        # self.learner.update(current_node, next_route, success=True)
        
        logger.info(f"🧭 Router selected: {next_route} (Target: {target_capability})")
        state.context_data['router_decision'] = next_route
        
        return state

    def _extract_capability(self, text: str) -> str:
        """Extract required capability from text."""
        # This could use an LLM or vector search
        return text

    def _simple_route(self, text: str) -> str:
        # Simple heuristic for now
        text = text.lower()
        if "math" in text or "calculate" in text:
            return "math_agent" if "math_agent" in self.routes else self.routes[0]
        if "code" in text or "python" in text:
            return "code_agent" if "code_agent" in self.routes else self.routes[0]
        
        # Default: Pick mostly used or random
        return self.routes[0]

    def condition(self, state: WorkflowState) -> str:
        """
        The condition function used in add_conditional_edge.
        """
        return state.context_data.get('router_decision', "__end__")
