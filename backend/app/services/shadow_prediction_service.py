"""
Shadow Mode Prediction Service - Phase 3

Responsibilities:
1. Execute "shadow" predictions in parallel, without affecting main execution path
2. Record prediction results vs actual results
3. Calculate prediction accuracy
4. No modification to user state or strategy
"""
from typing import List, Dict, Any, Optional
from loguru import logger
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import json

from app.orchestration.schemas import (
    ShadowPrediction, ExecutablePlan, RouteDecision
)


class ShadowPredictionService:
    """Shadow Mode Prediction Service

    Responsibilities:
    1. Generate "shadow" predictions for each request
    2. Predictions include:
       - Best execution mode (direct vs langgraph)
       - Predicted agents to be called
       - Predicted tools to be executed
    3. Compare with actual results, calculate accuracy
    4. Output to Redis/logs, no execution impact
    """

    SHADOW_REDIS_KEY_PREFIX = "shadow:prediction:"
    SHADOW_TTL = 86400  # 24 hours

    def __init__(self, redis_client=None):
        self.redis = redis_client

    async def predict_and_record(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        actual_decision: RouteDecision,
        actual_plan: Optional[ExecutablePlan] = None
    ) -> ShadowPrediction:
        """Generate prediction and record

        Args:
            user_message: User message
            user_id: User ID
            session_id: Session ID
            actual_decision: Actual routing decision
            actual_plan: Actual execution plan (if available)

        Returns:
            ShadowPrediction: Prediction result
        """
        # 1. Generate prediction
        prediction = self._generate_prediction(
            user_message, user_id, session_id
        )

        # 2. Record actual result
        prediction.actual_mode = actual_decision.execution_mode
        if actual_plan:
            prediction.actual_agents = actual_plan.agents_involved or []
            prediction.actual_tools = [tc.name for tc in actual_plan.tool_calls]
            prediction.plan_id = actual_plan.plan_id

        # 3. Calculate accuracy
        prediction.is_correct = self._evaluate_correctness(prediction)
        prediction.accuracy_score = self._calculate_accuracy(prediction)

        # 4. Persist
        await self._save_prediction(prediction)

        # 5. Log
        logger.info(
            f"Shadow prediction: mode={prediction.predicted_mode} "
            f"(actual={prediction.actual_mode}), "
            f"correct={prediction.is_correct}, "
            f"score={prediction.accuracy_score:.2f}"
        )

        return prediction

    def _generate_prediction(
        self,
        user_message: str,
        user_id: str,
        session_id: str
    ) -> ShadowPrediction:
        """Generate prediction (simplified version)

        In production, this could use ML models or more complex rules
        """
        msg_lower = user_message.lower()

        prediction = ShadowPrediction(
            user_id=user_id,
            session_id=session_id
        )

        # Predict execution mode
        complex_keywords = {
            "学习计划", "study plan", "制定计划", "复习策略",
            "时间安排", "schedule", "考试预测", "知识图谱"
        }
        is_complex = any(kw in msg_lower for kw in complex_keywords)

        if is_complex:
            prediction.predicted_mode = "langgraph"
            prediction.confidence = 0.75
        else:
            prediction.predicted_mode = "direct"
            prediction.confidence = 0.85

        # Predict agents
        if "知识" in msg_lower or "concept" in msg_lower or "图谱" in msg_lower:
            prediction.predicted_agents.append("galaxy_guide")
        if "考试" in msg_lower or "exam" in msg_lower or "重点" in msg_lower:
            prediction.predicted_agents.append("exam_oracle")
        if "时间" in msg_lower or "schedule" in msg_lower or "任务" in msg_lower:
            prediction.predicted_agents.append("time_tutor")

        # Predict tools
        tool_keywords = {
            "search_knowledge_graph": ["搜索", "知识", "search", "knowledge"],
            "analyze_past_papers": ["试卷", "真题", "past paper"],
            "predict_exam_focus": ["预测", "重点", "focus"],
            "create_task": ["任务", "task"],
            "suggest_pomodoro_schedule": ["番茄", "pomodoro", "schedule"]
        }

        for tool, keywords in tool_keywords.items():
            if any(kw in msg_lower for kw in keywords):
                prediction.predicted_tools.append(tool)

        return prediction

    def _evaluate_correctness(self, prediction: ShadowPrediction) -> bool:
        """Evaluate if prediction is correct"""
        # Mode prediction correct
        mode_correct = prediction.predicted_mode == prediction.actual_mode

        # Agents prediction correct (at least one match)
        agents_correct = (
            set(prediction.predicted_agents) & set(prediction.actual_agents)
        ) if prediction.actual_agents else True

        return mode_correct and agents_correct

    def _calculate_accuracy(self, prediction: ShadowPrediction) -> float:
        """Calculate accuracy score"""
        score = 0.0
        max_score = 3.0

        # Mode prediction (weight 1.0)
        if prediction.predicted_mode == prediction.actual_mode:
            score += 1.0

        # Agents prediction (weight 1.0)
        if prediction.actual_agents:
            predicted_set = set(prediction.predicted_agents)
            actual_set = set(prediction.actual_agents)
            if predicted_set:
                precision = len(predicted_set & actual_set) / len(predicted_set)
                recall = len(predicted_set & actual_set) / len(actual_set)
                score += (precision + recall) / 2

        # Tools prediction (weight 1.0)
        if prediction.actual_tools:
            predicted_tools = set(prediction.predicted_tools)
            actual_tools = set(prediction.actual_tools)
            if predicted_tools:
                tool_score = len(predicted_tools & actual_tools) / len(predicted_tools)
                score += tool_score

        return score / max_score

    async def _save_prediction(self, prediction: ShadowPrediction):
        """Save prediction to Redis"""
        if not self.redis:
            return

        key = f"{self.SHADOW_REDIS_KEY_PREFIX}{prediction.prediction_id}"
        try:
            payload = json.dumps({
                "prediction_id": prediction.prediction_id,
                "plan_id": prediction.plan_id,
                "user_id": prediction.user_id,
                "session_id": prediction.session_id,
                "timestamp": prediction.timestamp,
                "predicted_mode": prediction.predicted_mode,
                "predicted_agents": prediction.predicted_agents,
                "predicted_tools": prediction.predicted_tools,
                "confidence": prediction.confidence,
                "actual_mode": prediction.actual_mode,
                "actual_agents": prediction.actual_agents,
                "actual_tools": prediction.actual_tools,
                "is_correct": prediction.is_correct,
                "accuracy_score": prediction.accuracy_score
            })
            await self.redis.setex(key, self.SHADOW_TTL, payload)
        except Exception as e:
            logger.warning(f"Failed to save shadow prediction: {e}")

    async def get_accuracy_stats(
        self,
        user_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get prediction accuracy statistics

        Args:
            user_id: User ID (optional)
            hours: Time range in hours

        Returns:
            Dict with:
            - total_predictions: Total predictions
            - correct_count: Correct count
            - accuracy_rate: Accuracy rate
            - avg_confidence: Average confidence
            - mode_accuracy: Accuracy per mode
        """
        if not self.redis:
            return {}

        # Simplified implementation: scan and aggregate from Redis
        # In production, should use time series DB or dedicated analytics

        return {
            "total_predictions": 0,
            "correct_count": 0,
            "accuracy_rate": 0.0,
            "avg_confidence": 0.0,
            "mode_accuracy": {}
        }


# Global instance
shadow_prediction_service = ShadowPredictionService()
