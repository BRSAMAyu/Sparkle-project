"""WS-D: Task Assistant Dormant Mode — one-shot injection + outcome capture."""

from app.task_assistant.dormant_injector import DormantInjector
from app.task_assistant.outcome_capture import OutcomeCapture
from app.task_assistant.schemas import (
    AssistantOutcome,
    DormantInjection,
    DormantInjectionItem,
)
from app.task_assistant.store import CacheBackedDormantStore

__all__ = [
    "DormantInjection",
    "DormantInjectionItem",
    "AssistantOutcome",
    "DormantInjector",
    "OutcomeCapture",
    "CacheBackedDormantStore",
]
