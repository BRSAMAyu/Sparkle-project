from typing import Optional, List, Dict
from loguru import logger
import numpy as np

class SemanticRouter:
    """Based on semantic similarity intelligent routing"""
    
    def __init__(self, embedding_service, knowledge_graph=None):
        self.embedding = embedding_service
        self.kg = knowledge_graph
        self.capability_map = {
            'math': ['数学', '计算', '公式', '方程', '算术', 'calculate', 'math', 'equation'],
            'code': ['代码', '编程', 'python', 'javascript', '开发', 'code', 'programming'],
            'knowledge': ['搜索', '查询', '知识', '信息', '资料', 'search', 'query', 'info'],
            'planning': ['计划', '规划', '安排', '任务分解', 'plan', 'schedule'],
            'reasoning': ['推理', '逻辑', '分析', '思考', 'reasoning', 'logic'],
            'writing': ['写作', '创作', '文章', '文案', 'write', 'draft'],
            'translation': ['翻译', '语言', '多语言', 'translate', 'language'],
            'data_analysis': ['分析', '统计', '数据', '图表', 'analysis', 'stats']
        }
    
    async def route(self, query: str, context: Dict) -> Optional[str]:
        """Route based on semantic similarity"""
        try:
            query_vec = await self.embedding.get_embedding(query)
            similarities = {}
            
            for capability, keywords in self.capability_map.items():
                # Keyword matching score
                keyword_score = sum(1 for kw in keywords if kw in query.lower()) / len(keywords)
                keyword_score = min(keyword_score * 5, 1.0) # Normalize a bit
                
                if self.kg and hasattr(self.kg, 'get_related_concepts'):
                    semantic_score = await self._kg_similarity(query_vec, capability)
                else:
                    # Fallback if no KG: use embedding similarity with keywords (conceptually)
                    # For now just use keyword_score or 0 if we don't pre-calculate keyword embeddings
                    semantic_score = 0.0
                
                similarities[capability] = {
                    'keyword': keyword_score,
                    'semantic': semantic_score,
                    'combined': keyword_score * 0.3 + semantic_score * 0.7 if self.kg else keyword_score
                }
            
            best_capability = None
            best_score = 0
            
            for capability, scores in similarities.items():
                if scores['combined'] > best_score and scores['combined'] > 0.3: # Threshold 0.3
                    best_score = scores['combined']
                    best_capability = capability
            
            if best_capability:
                logger.info(f"Semantic routing: '{query}' -> {best_capability} (score: {best_score:.2f})")
                return best_capability
            
            return None
            
        except Exception as e:
            logger.error(f"Semantic routing failed: {e}")
            return None
    
    async def _kg_similarity(self, query_vec: List[float], capability: str) -> float:
        """Calculate similarity from knowledge graph"""
        if not self.kg:
            return 0.0
        
        concepts = await self.kg.get_related_concepts(capability)
        if not concepts:
            return 0.0
        
        similarities = []
        for concept in concepts:
            concept_vec = await self.embedding.get_embedding(concept)
            sim = self._cosine_similarity(query_vec, concept_vec)
            similarities.append(sim)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity"""
        if not vec1 or not vec2:
            return 0.0
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

class HybridRouter:
    """Hybrid Router: Rules + Semantic + Graph"""
    
    def __init__(self, graph_router, semantic_router, user_preferences=None):
        self.graph = graph_router
        self.semantic = semantic_router
        self.user_pref = user_preferences or {}
    
    async def find_route(self, current: str, query: str, context: Dict) -> Optional[str]:
        """Multi-strategy routing decision"""
        # 1. Rule-based (Fastest)
        rule_result = self._apply_rules(query, context)
        if rule_result:
            return rule_result
        
        # 2. Semantic Routing (Smart)
        semantic_result = await self.semantic.route(query, context)
        # Check if the semantic result maps to a node in the graph
        # Assuming capability name might map to node name or need mapping
        if semantic_result:
             # Basic mapping: capability "math" -> "math_agent"
            target_node = f"{semantic_result}_agent"
            if target_node in self.graph.graph.nodes():
                return target_node
        
        # 3. Graph Routing (Fallback/Standard)
        # Extract capability/intent from query if possible, or use semantic result
        capability = semantic_result if semantic_result else self._extract_capability(query)
        if capability:
            # Map capability to node inside graph router if it handles it
            graph_result = self.graph.find_route(current, capability)
            if graph_result:
                return graph_result
        
        # 4. Default Routing
        return "orchestrator"
    
    def _apply_rules(self, query: str, context: Dict) -> Optional[str]:
        """Hardcoded rules"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['error', 'bug', '失败', '错误']):
            return "debug_agent" if "debug_agent" in self.graph.graph.nodes() else None
        
        if any(word in query_lower for word in ['calculate', '计算', '等于', '+', '-', '*', '/']):
            return "math_agent" if "math_agent" in self.graph.graph.nodes() else None
        
        if any(word in query_lower for word in ['code', 'python', 'javascript', '编程', '代码']):
            return "code_agent" if "code_agent" in self.graph.graph.nodes() else None
        
        return None
    
    def _extract_capability(self, text: str) -> str:
        """Extract capability keyword from text"""
        text_lower = text.lower()
        for capability, keywords in self.semantic.capability_map.items():
            if any(kw in text_lower for kw in keywords):
                return capability
        return ""
