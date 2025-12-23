from pydantic import BaseModel
from datetime import date
from typing import Optional

class DailyMetricResponse(BaseModel):
    date: date
    total_focus_minutes: int
    tasks_completed: int
    tasks_created: int
    nodes_studied: int
    mastery_gained: float
    review_count: int
    anxiety_score: float
    chat_messages_count: int

    class Config:
        from_attributes = True

class UserAnalyticsSummary(BaseModel):
    summary: str
