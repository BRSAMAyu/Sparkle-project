import networkx as nx
from typing import List, Dict, Any, Optional
from loguru import logger

class GraphBasedRouter:
    """
    Intelligent Router using NetworkX.
    Calculates optimal paths based on cost, latency, and success rate.
    """
    def __init__(self, redis_client=None):
        self.graph = nx.DiGraph()
        self._initialize_graph()
        
        # Performance Optimization (Route Cache)
        self.cache = None
        self.precomputed_router = None
        
        if redis_client:
            from app.routing.route_cache import RouteCache, PrecomputedRouter
            self.cache = RouteCache(redis_client)
            self.precomputed_router = PrecomputedRouter(self, self.cache)

    def _initialize_graph(self):
        """
        Initialize the routing graph.
        Nodes represent Agents or Capabilities.
        Edges represent transitions with weights.
        """
        # Define agents/nodes
        agents = ["orchestrator", "math_agent", "code_agent", "knowledge_agent", "planner"]
        self.graph.add_nodes_from(agents)
        
        # Define transitions (edges) with initial weights
        # Weight can represent "cost" or "inverse success rate"
        # Lower weight = better path
        
        # Orchestrator can go anywhere
        for agent in agents:
            if agent != "orchestrator":
                self.graph.add_edge("orchestrator", agent, weight=1.0)
        
        # Specialized agents usually return to orchestrator
        for agent in agents:
            if agent != "orchestrator":
                self.graph.add_edge(agent, "orchestrator", weight=0.5)
                
        # Some specialized transitions
        self.graph.add_edge("planner", "code_agent", weight=0.8)
        self.graph.add_edge("planner", "math_agent", weight=0.8)

    async def find_route(self, current_node: str, target_capability: str) -> Optional[str]:
        """
        Find the next hop to satisfy the target capability.
        """
        # Map capability to target node
        target_node = self._map_capability_to_node(target_capability)
        if not target_node:
            return None
            
        if target_node == current_node:
            return None
        
        # Use precomputed/cached router if available
        if self.precomputed_router:
            return await self.precomputed_router.find_route(current_node, target_node)
            
        try:
            path = nx.shortest_path(self.graph, source=current_node, target=target_node, weight="weight")
            if len(path) > 1:
                return path[1] # Return next hop
        except nx.NetworkXNoPath:
            logger.warning(f"No path found from {current_node} to {target_node}")
            return None
        return None

    def _map_capability_to_node(self, capability: str) -> str:
        """Map user intent/capability to a node name."""
        if "math" in capability or "calculate" in capability:
            return "math_agent"
        if "code" in capability or "python" in capability:
            return "code_agent"
        if "search" in capability or "knowledge" in capability:
            return "knowledge_agent"
        if "plan" in capability:
            return "planner"
        return "orchestrator"

    def update_weight(self, u: str, v: str, success: bool, latency: float):
        """
        Update edge weights based on feedback (Phase 4 integration).
        """
        if self.graph.has_edge(u, v):
            current_weight = self.graph[u][v]['weight']
            # Simple decay/update logic
            # If success, decrease weight (cost). If fail, increase weight.
            if success:
                new_weight = current_weight * 0.95
            else:
                new_weight = current_weight * 1.2
            
            self.graph[u][v]['weight'] = max(0.1, min(new_weight, 10.0))
            
            # Invalidate cache if weight changed significantly
            if self.cache:
                self.cache.invalidate(u, v)
