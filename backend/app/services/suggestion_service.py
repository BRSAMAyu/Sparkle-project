from typing import List, Dict, Any
from loguru import logger

class SuggestionService:
    """
    智能建议服务 (Vision Item 3: Real-time Intent Prediction)
    
    Responsibilities:
    1. Provide real-time auto-completion/next-step suggestions based on user input.
    2. Combine rule-based heuristics (fast) with AI-based prediction (smart).
    """

    def __init__(self):
        # Basic heuristic rules
        self.rules = {
            "create": ["Create a new task", "Create a study plan", "Create a new habit"],
            "plan": ["Plan my week", "Plan for exam", "Sprint planning"],
            "review": ["Review today's tasks", "Review weekly progress", "Start flashcard review"],
            "analy": ["Analyze my behavior (Prism)", "Analyze study time"],
            "trans": ["Translate this text", "Translate to Chinese"],
            "spr": ["Start Sprint Mode", "Enter Focus Mode"],
            "b": ["Behavior Report", "Back to Home"]
        }

    async def predict_intent(self, query: str, user_id: str) -> List[Dict[str, str]]:
        """
        Predict user intent based on partial input.
        """
        query_lower = query.lower()
        suggestions = []

        # 1. Exact/Prefix Match from Rules
        for key, templates in self.rules.items():
            if key in query_lower:
                for t in templates:
                    suggestions.append({
                        "text": t,
                        "type": "command",
                        "confidence": 0.9 if query_lower == key else 0.7
                    })

        # 2. Context-Aware Suggestions (Placeholder for AI/History)
        # TODO: Fetch recent user context or use a small language model
        if len(query) > 5 and not suggestions:
             suggestions.append({
                 "text": f"Ask about '{query}'",
                 "type": "chat",
                 "confidence": 0.5
             })

        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions[:5]

suggestion_service = SuggestionService()
