from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.config import settings


class ModelTier(str, Enum):
    EDGE = "EDGE"
    STD = "STD"
    HIGH = "HIGH"


@dataclass(frozen=True)
class ModelRoute:
    model_name: str
    tier: ModelTier
    temperature: float = 0.5


class ModelRouter:
    def route(
        self,
        task_type: str,
        complexity: float | None = None,
        sensitive: bool = False,
    ) -> ModelRoute:
        if sensitive or (complexity is not None and complexity >= 0.7):
            return ModelRoute(
                model_name=settings.LLM_REASON_MODEL_NAME or settings.LLM_MODEL_NAME,
                tier=ModelTier.HIGH,
                temperature=0.3,
            )
        if task_type.startswith("light_") or (complexity is not None and complexity <= 0.3):
            return ModelRoute(
                model_name=settings.LLM_MODEL_NAME,
                tier=ModelTier.EDGE,
                temperature=0.6,
            )
        return ModelRoute(
            model_name=settings.LLM_MODEL_NAME,
            tier=ModelTier.STD,
            temperature=0.5,
        )
