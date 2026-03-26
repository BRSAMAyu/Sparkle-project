from __future__ import annotations

from enum import Enum


class LearningSimulationState(str, Enum):
    CREATED = "CREATED"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
