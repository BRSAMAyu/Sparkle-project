"""
Core: intelligence
Phase: adapt
Stage: Signal-to-Action Spine — ML Recall Ranking

Lightweight ML models for recall opportunity scoring.
No external ML framework dependencies — uses pure Python decision trees
and logistic regression trained on OutcomeRecorder history.
"""

from app.services.ml.recall_ranker import RecallRanker, RecallFeatures

__all__ = ["RecallRanker", "RecallFeatures"]
