from __future__ import annotations

import json
import time
from typing import Any, Dict

from loguru import logger

from app.schemas.analysis import AnalysisTaskInput, AnalysisResult
from app.services.analysis.model_router import ModelRouter
from app.services.llm_service import llm_service


class AnalysisOrchestrator:
    def __init__(self) -> None:
        self.model_router = ModelRouter()

    async def run_task(self, task: AnalysisTaskInput) -> AnalysisResult:
        start = time.perf_counter()
        route = self.model_router.route(
            task_type=task.task_type,
            complexity=task.context.get("complexity"),
            sensitive=task.context.get("sensitive", False),
        )

        if task.task_type == "behavior_pattern_from_fragment":
            result = await self._run_behavior_pattern(task, route.model_name, route.temperature)
        else:
            result = AnalysisResult(
                task_id=task.task_id,
                task_type=task.task_type,
                model_used=route.model_name,
                status="unsupported",
            )

        result.latency_ms = int((time.perf_counter() - start) * 1000)
        result.model_used = result.model_used or route.model_name
        result.evidence_refs = task.evidence_refs
        return result

    async def _run_behavior_pattern(
        self,
        task: AnalysisTaskInput,
        model_name: str,
        temperature: float,
    ) -> AnalysisResult:
        payload = task.payload
        prompt = _build_behavior_prompt(payload)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert Cognitive Behavioral Therapist and Learning Coach. "
                    "Output valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response_text = await llm_service.chat(messages, model=model_name, temperature=temperature)
        analysis = _parse_json_response(response_text)
        if analysis is None:
            logger.warning(f"Analysis parsing failed for task {task.task_id}")
            return AnalysisResult(
                task_id=task.task_id,
                task_type=task.task_type,
                model_used=model_name,
                status="error",
                metadata={"error": "Invalid JSON from LLM"},
            )

        return AnalysisResult(
            task_id=task.task_id,
            task_type=task.task_type,
            model_used=model_name,
            status="ok",
            confidence=float(analysis.get("confidence_score", 0.0) or 0.0),
            primary_output=analysis,
        )


def _build_behavior_prompt(payload: Dict[str, Any]) -> str:
    similar_text = payload.get("similar_text", "")
    return f"""
            Analyze this behavioral error/thought:
            User Input: "{payload.get('fragment_content', '')}"
            Context: {payload.get('context_tags')}
            Error Tags: {payload.get('error_tags')}
            Severity: {payload.get('severity', 1)}/5
            
            Similar Past Events (RAG Context):
            {similar_text}
            
            User Profile:
            {payload.get('user_summary', '')}
            
            Task:
            1. Identify the Root Cause.
            2. Identify Pattern.
            3. Suggest SMART Intervention.
            4. Provide Confidence Score (0.0 - 1.0).
            
            Output JSON Format:
            {{
                "root_cause": "...",
                "pattern_name": "...",
                "pattern_type": "cognitive/emotional/execution",
                "description": "...",
                "solution_text": "...",
                "confidence_score": 0.85
            }}
            """


def _parse_json_response(response_text: str) -> Dict[str, Any] | None:
    try:
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        return None
