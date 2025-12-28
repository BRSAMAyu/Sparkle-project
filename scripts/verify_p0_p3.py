import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")

class TestP0ToP3Implementation(unittest.IsolatedAsyncioTestCase):
    
    async def test_p0_production_readiness(self):
        logger.info("Verifying P0: Production Readiness (Bayesian Learner, Router, Metrics)...")
        
        # 1. PersistentBayesianLearner
        try:
            from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
            mock_redis = AsyncMock()
            learner = PersistentBayesianLearner(mock_redis, "test_user_id")
            self.assertIsNotNone(learner)
            logger.info("✅ PersistentBayesianLearner imported and instantiated.")
        except ImportError as e:
            self.fail(f"Failed to import PersistentBayesianLearner: {e}")

        # 2. SemanticRouter / HybridRouter
        try:
            from app.routing.semantic_router import SemanticRouter
            # router = SemanticRouter() # Might need embedding model, skipping instantiation
            logger.info("✅ SemanticRouter imported.")
        except ImportError as e:
            self.fail(f"Failed to import SemanticRouter: {e}")

        # 3. BusinessMetrics
        try:
            from app.core.business_metrics import BusinessMetricsCollector
            metrics = BusinessMetricsCollector()
            logger.info("✅ BusinessMetricsCollector imported and instantiated.")
        except ImportError as e:
            self.fail(f"Failed to import BusinessMetricsCollector: {e}")

    async def test_p1_architecture_refactor(self):
        logger.info("Verifying P1: Architecture Refactor (Statecharts, Standard Workflow)...")
        
        # 1. Statechart Engine
        try:
            from app.orchestration.statechart_engine import StateGraph, WorkflowState
            graph = StateGraph("TestGraph")
            self.assertEqual(graph.name, "TestGraph")
            logger.info("✅ StateGraph imported and instantiated.")
        except ImportError as e:
            self.fail(f"Failed to import StateGraph: {e}")
            
        # 2. Standard Workflow
        try:
            from app.agents.standard_workflow import create_standard_chat_graph
            graph = create_standard_chat_graph()
            self.assertIsInstance(graph, StateGraph)
            logger.info("✅ Standard Chat Graph created.")
        except ImportError as e:
             self.fail(f"Failed to import standard_workflow: {e}")

    async def test_p2_experience_upgrade(self):
        logger.info("Verifying P2: Experience Upgrade (Visualizer, Tracer)...")
        
        # 1. RealtimeVisualizer
        try:
            from app.visualization.realtime_visualizer import RealtimeVisualizer
            logger.info("✅ RealtimeVisualizer imported.")
        except ImportError as e:
            self.fail(f"Failed to import RealtimeVisualizer: {e}")

        # 2. ExecutionTracer
        try:
            from app.visualization.execution_tracer import ExecutionTracer
            mock_redis = AsyncMock()
            tracer = ExecutionTracer(mock_redis)
            self.assertIsNotNone(tracer)
            logger.info("✅ ExecutionTracer imported and instantiated.")
        except ImportError as e:
            self.fail(f"Failed to import ExecutionTracer: {e}")

    async def test_p3_intelligent_optimization(self):
        logger.info("Verifying P3: Intelligent Optimization (Exploration, Optimizer, AB Test)...")
        
        # 1. ExplorationRouter
        try:
            from app.routing.exploration_router import ExplorationRouter
            # Needs a learner
            mock_redis = AsyncMock()
            from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
            learner = PersistentBayesianLearner(mock_redis, "test_user_id")
            
            router = ExplorationRouter(learner=learner)
            self.assertIsNotNone(router)
            logger.info("✅ ExplorationRouter imported and instantiated.")
        except ImportError as e:
            self.fail(f"Failed to import ExplorationRouter: {e}")

        # 2. AutoOptimizer
        try:
            from app.learning.auto_optimizer import AutoOptimizer
            # Needs graph_router and learner
            mock_router = MagicMock()
            from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
            mock_learner = PersistentBayesianLearner(AsyncMock(), "test_user")
            
            optimizer = AutoOptimizer(
                redis_client=AsyncMock(),
                graph_router=mock_router,
                learner=mock_learner
            )
            logger.info("✅ AutoOptimizer imported and instantiated.")
        except ImportError as e:
             self.fail(f"Failed to import AutoOptimizer: {e}")

        # 3. RouteCache
        try:
            from app.routing.route_cache import RouteCache
            cache = RouteCache(redis_client=AsyncMock())
            logger.info("✅ RouteCache imported.")
        except ImportError as e:
             self.fail(f"Failed to import RouteCache: {e}")

        # 4. ABTestFramework
        try:
            from app.learning.ab_test_framework import ABTestFramework
            ab = ABTestFramework(redis_client=AsyncMock())
            logger.info("✅ ABTestFramework imported.")
        except ImportError as e:
             self.fail(f"Failed to import ABTestFramework: {e}")
             
        # 5. MultiDimensionalLearner
        try:
            from app.learning.multi_dimensional_learner import MultiDimensionalLearner
            learner = MultiDimensionalLearner(redis_client=AsyncMock(), user_id="test_user")
            logger.info("✅ MultiDimensionalLearner imported.")
        except ImportError as e:
             self.fail(f"Failed to import MultiDimensionalLearner: {e}")

if __name__ == '__main__':
    unittest.main()
