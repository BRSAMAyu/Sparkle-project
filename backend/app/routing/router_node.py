from typing import List, Dict, Any, Optional
from loguru import logger
import random

from app.orchestration.statechart_engine import WorkflowState
from app.routing.graph_router import GraphBasedRouter
from app.learning.bayesian_learner import BayesianLearner
from app.core.business_metrics import track_routing_decision, metrics_collector
from app.routing.exploration_router import HybridExplorationRouter

class RouterNode:
    """
    Intelligent Router Node.
    Decides the next step in the workflow based on state and history.
    
    Integrates Graph-based routing (Phase 2) and Bayesian Learning (Phase 4).
    """
    def __init__(self, routes: List[str], redis_client=None, user_id: Optional[str] = None):
        self.routes = routes
        self.graph_router = GraphBasedRouter()
        
        # Initialize semantic and hybrid routers
        from app.services.embedding_service import embedding_service
        from app.routing.semantic_router import SemanticRouter, HybridRouter
        
        self.semantic_router = SemanticRouter(
            embedding_service=embedding_service,
            knowledge_graph=None # KG requires db_session, skipping for now
        )
        
        self.hybrid_router = HybridRouter(
            graph_router=self.graph_router,
            semantic_router=self.semantic_router
        )
        
        if redis_client and user_id:
            from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
            self.learner = PersistentBayesianLearner(redis_client, user_id)
        else:
            self.learner = BayesianLearner()
            
        # Initialize Exploration Router
        self.exploration_router = HybridExplorationRouter(self.learner, user_id)

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        """
        Execute routing logic.
        Updates state.context_data['next_step']
        """
        last_msg = state.messages[-1]['content'] if state.messages else ""
        current_node = state.context_data.get("current_node", "orchestrator")
        
        # 1. Get Candidate Routes (Hybrid + Neighbors)
        target_capability = self._extract_capability(last_msg)
        candidates = await self._get_candidate_routes(current_node, last_msg, state.context_data)
        
        # 2. Exploration Selection
        if candidates:
            # Use exploration router to pick one
            next_route = await self.exploration_router.select_route(
                source=current_node,
                targets=candidates,
                context=state.context_data
            )
        else:
            # Fallback to simple logic if no candidates found via graph/exploration
            next_route = self._simple_route(last_msg)

        # 3. Metrics Update
        prob = 0.5
        if next_route:
            prob = await self.learner.get_probability(current_node, next_route)
            metrics_collector.update_route_probability(current_node, next_route, prob)
            
            if prob < 0.3:
                logger.warning(f"Low probability route {current_node}->{next_route} ({prob:.2f})")
        
        logger.info(f"🧭 Router selected: {next_route} (Confidence: {prob:.2f})")
        
        state.context_data['router_decision'] = next_route
        state.context_data['router_confidence'] = prob if next_route else 0.0
        
        return state

    @track_routing_decision(method="hybrid")
    async def find_route_with_metrics(self, current: str, query: str, context: Dict) -> Optional[str]:
        """Route with metrics tracking"""
        return await self.hybrid_router.find_route(current, query, context)

    async def _get_candidate_routes(self, current: str, query: str, context: Dict) -> List[str]:
        """Get list of candidate routes."""
        candidates = set()
        
        # 1. Hybrid Router suggestion
        hybrid_route = await self.find_route_with_metrics(current, query, context)
        if hybrid_route:
            candidates.add(hybrid_route)
            
        # 2. Graph Neighbors (valid transitions)
        if current in self.graph_router.graph.nodes():
            neighbors = list(self.graph_router.graph.neighbors(current))
            candidates.update(neighbors)
            
        return list(candidates)

    def condition(self, state: WorkflowState) -> str:
        """
        The condition function used in add_conditional_edge.
        """
        return state.context_data.get('router_decision', "__end__")
