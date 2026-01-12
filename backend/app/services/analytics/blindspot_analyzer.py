from typing import List, Dict, Any, Tuple, Optional
import networkx as nx
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus

class BlindspotAnalyzer:
    """
    Blindspot Analyzer Service
    Identifies knowledge gaps (blindspots) in the user's knowledge graph.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_blindspots(self, user_id: str, subject_id: int = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Identify blindspots: high-importance nodes with low mastery or missing prerequisites.
        """
        # 1. Fetch relevant graph data
        nodes, edges, statuses = await self._fetch_graph_data(user_id, subject_id)
        
        if not nodes:
            return []

        # 2. Build Graph
        G = nx.DiGraph()
        node_map = {}
        
        for node in nodes:
            G.add_node(node.id, importance=node.importance_level, name=node.name)
            node_map[node.id] = node

        for edge in edges:
            G.add_edge(edge.source_node_id, edge.target_node_id, type=edge.relation_type)

        # 3. Analyze for Blindspots
        # Criteria:
        # - High importance (>3)
        # - Low mastery (<30%) or Unlocked but not studied
        # - Has prerequisites that ARE mastered (so it's accessible but neglected) -> "Accessible Blindspot"
        # - OR: Is a prerequisite for a goal node (if we had goals, skipping for MVP)
        
        status_map = {s.node_id: s for s in statuses}
        blindspots = []

        for node in nodes:
            node_id = node.id
            status = status_map.get(node_id)
            
            mastery = status.mastery_score if status else 0
            
            # Filter 1: Is it a "gap"? (Low mastery)
            if mastery >= 60: # Threshold for "okay"
                continue
                
            # Filter 2: Importance
            if node.importance_level < 3:
                continue
                
            # Filter 3: Accessibility (Are parents/prereqs mastered?)
            # Get predecessors (prerequisites)
            prereqs = [n for n in G.predecessors(node_id) 
                       if G.get_edge_data(n, node_id).get('type') == 'prerequisite']
            
            total_prereqs = len(prereqs)
            mastered_prereqs = 0
            for pid in prereqs:
                p_status = status_map.get(pid)
                if p_status and p_status.mastery_score >= 60:
                    mastered_prereqs += 1
            
            # Logic: If >70% of prereqs are mastered, but this node isn't, it's a bottleneck/blindspot.
            # If no prereqs, it's a root node blindspot (foundational gap).
            
            is_accessible = False
            if total_prereqs == 0:
                is_accessible = True # Foundational
            elif mastered_prereqs / total_prereqs >= 0.7:
                is_accessible = True
            
            if is_accessible:
                score = self._calculate_blindspot_score(node, mastery, is_accessible)
                blindspots.append({
                    "node_id": str(node.id),
                    "node_name": node.name,
                    "reason": "Foundational gap" if total_prereqs == 0 else "Bottleneck: Prerequisites mastered but node neglected",
                    "importance": node.importance_level,
                    "current_mastery": mastery,
                    "score": score
                })

        # Sort by score descending
        blindspots.sort(key=lambda x: x['score'], reverse=True)
        return blindspots[:limit]

    def _calculate_blindspot_score(self, node: KnowledgeNode, mastery: float, accessible: bool) -> float:
        """Calculate a priority score for the blindspot."""
        # Simple heuristic: Importance * (100 - Mastery)
        # Boost if accessible
        base_score = node.importance_level * (100 - mastery)
        if accessible:
            base_score *= 1.2
        return base_score

    async def _fetch_graph_data(self, user_id: str, subject_id: Optional[int]) -> Tuple[List[KnowledgeNode], List[NodeRelation], List[UserNodeStatus]]:
        """Fetch nodes, edges, and user statuses for analysis."""
        
        # Nodes
        query_nodes = select(KnowledgeNode)
        if subject_id:
            query_nodes = query_nodes.where(KnowledgeNode.subject_id == subject_id)
        # Limit to reasonable size for MVP analysis if graph is huge
        query_nodes = query_nodes.limit(500) 
        
        result_nodes = await self.db.execute(query_nodes)
        nodes = result_nodes.scalars().all()
        node_ids = [n.id for n in nodes]
        
        if not node_ids:
            return [], [], []

        # Edges (Internal to the fetched nodes)
        query_edges = select(NodeRelation).where(
            NodeRelation.source_node_id.in_(node_ids),
            NodeRelation.target_node_id.in_(node_ids)
        )
        result_edges = await self.db.execute(query_edges)
        edges = result_edges.scalars().all()

        # Statuses
        query_statuses = select(UserNodeStatus).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.node_id.in_(node_ids)
        )
        result_statuses = await self.db.execute(query_statuses)
        statuses = result_statuses.scalars().all()

        return nodes, edges, statuses
